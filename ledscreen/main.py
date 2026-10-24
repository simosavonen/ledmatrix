import argparse
import time
from datetime import datetime, timedelta

from .canvas import Canvas
from .modes.aquarium import AquariumMode
from .modes.clock import ClockMode
from .modes.ecosystem import EcosystemMode
from .modes.life import LifeMode
from .modes.matrixrain import MatrixRainMode
from .modes.pong import PongMode
from .modes.sand import SandMode
from .rotation import RotationController

FPS = 30

MODES = {
    "clock": ClockMode,
    "matrix_rain": MatrixRainMode,
    "life": LifeMode,
    "ecosystem": EcosystemMode,
    "sand": SandMode,
    "aquarium": AquariumMode,
    "pong": PongMode,
}


def build_rotation(fun_every: float, fun_duration: float) -> RotationController:
    anchor = ClockMode()
    fun_modes = [MatrixRainMode(), LifeMode(), EcosystemMode(), SandMode(), AquariumMode(), PongMode()]
    return RotationController(
        anchor=anchor,
        fun_modes=fun_modes,
        fun_every=timedelta(minutes=fun_every),
        fun_duration=timedelta(seconds=fun_duration),
    )


def run_live(display, fun_every: float, fun_duration: float) -> None:
    rotation = build_rotation(fun_every, fun_duration)
    canvas = Canvas(display.width, display.height)
    period = 1.0 / FPS
    try:
        while True:
            start = time.monotonic()
            now = datetime.now()
            mode = rotation.current_mode(now)
            mode.render(canvas, now)
            display.show(canvas)
            elapsed = time.monotonic() - start
            time.sleep(max(0.0, period - elapsed))
    except KeyboardInterrupt:
        pass
    finally:
        display.close()


def run_snapshot(display, mode_name: str, duration: float, out_path: str) -> None:
    mode = MODES[mode_name]()
    canvas = Canvas(display.width, display.height)
    period = 1.0 / FPS
    end_time = time.monotonic() + duration
    while time.monotonic() < end_time:
        now = datetime.now()
        mode.render(canvas, now)
        display.show(canvas)
        time.sleep(period)
    display.save_snapshot(out_path)
    display.close()
    print(f"Saved snapshot to {out_path}")


def main() -> None:
    parser = argparse.ArgumentParser(description="LED wall screen controller")
    parser.add_argument(
        "--sim", action="store_true", help="run against the on-screen simulator instead of real hardware"
    )
    parser.add_argument(
        "--snapshot",
        metavar="PATH",
        help="headless: run a single mode briefly and save a PNG snapshot, then exit",
    )
    parser.add_argument("--mode", choices=list(MODES), default="clock", help="mode to use with --snapshot")
    parser.add_argument("--duration", type=float, default=3.0, help="seconds to run before --snapshot")
    parser.add_argument("--fun-every", type=float, default=5.0, help="minutes between fun-mode breaks")
    parser.add_argument("--fun-duration", type=float, default=45.0, help="seconds each fun-mode break lasts")
    parser.add_argument("--brightness", type=int, default=30, help="real hardware only, percent 1-100")
    parser.add_argument("--gpio-slowdown", type=int, default=4, help="real hardware only")
    args = parser.parse_args()

    if args.snapshot:
        from .display.sim import SimDisplay

        display = SimDisplay(live=False)
        run_snapshot(display, args.mode, args.duration, args.snapshot)
        return

    if args.sim:
        from .display.sim import SimDisplay

        display = SimDisplay(live=True)
    else:
        from .display.matrix import MatrixDisplay

        display = MatrixDisplay(brightness=args.brightness, gpio_slowdown=args.gpio_slowdown)

    run_live(display, args.fun_every, args.fun_duration)


if __name__ == "__main__":
    main()
