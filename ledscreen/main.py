import argparse
import time
from datetime import datetime

from .canvas import Canvas
from .modes.analog_clock import AnalogClockMode
from .modes.aquarium import AquariumMode
from .modes.clock import ClockMode
from .modes.ecosystem import EcosystemMode
from .modes.gauge_clock import GaugeClockMode
from .modes.giant_clock import GiantClockMode
from .modes.life import LifeMode
from .modes.orbit_clock import OrbitClockMode
from .modes.pong import PongMode
from .modes.race import RaceMode
from .modes.rings_clock import RingsClockMode
from .modes.sand import SandMode
from .modes.tetris import TetrisMode
from .modes.thick_ring_clock import ThickRingClockMode
from .rotation import RotationController

FPS = 30

MODES = {
    "clock": ClockMode,
    "analog_clock": AnalogClockMode,
    "orbit_clock": OrbitClockMode,
    "rings_clock": RingsClockMode,
    "gauge_clock": GaugeClockMode,
    "giant_clock": GiantClockMode,
    "thick_ring_clock": ThickRingClockMode,
    "life": LifeMode,
    "ecosystem": EcosystemMode,
    "sand": SandMode,
    "aquarium": AquariumMode,
    "pong": PongMode,
    "race": RaceMode,
    "tetris": TetrisMode,
}


def build_rotation(clock_lead: float, fun_duration: float) -> RotationController:
    # rings_clock, giant_clock, and thick_ring_clock dropped from rotation
    # per readability review - no exact digits on screen at a glance
    # (rings_clock, thick_ring_clock) or the full time never fully visible
    # at once (giant_clock panning off-screen). Kept importable (and in
    # MODES, for --only preview) so nothing is lost, just excluded here.
    clock_modes = [
        ClockMode(),
        AnalogClockMode(),
        OrbitClockMode(),
        GaugeClockMode(),
    ]
    # Fun modes disabled per user feedback: the wall display needs to stay
    # readable as a clock/date/weather screen at a glance, not cut away to
    # games/sims. Kept importable (and in MODES, for --only preview) so
    # nothing is lost, just excluded from the live rotation.
    fun_modes: list = []
    return RotationController(
        clock_modes=clock_modes,
        fun_modes=fun_modes,
        clock_lead=clock_lead,
        fun_duration=fun_duration,
    )


def run_live(display, clock_lead: float, fun_duration: float) -> None:
    rotation = build_rotation(clock_lead, fun_duration)
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


def run_single(display, mode_name: str) -> None:
    mode = MODES[mode_name]()
    canvas = Canvas(display.width, display.height)
    period = 1.0 / FPS
    try:
        while True:
            start = time.monotonic()
            now = datetime.now()
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
    parser.add_argument(
        "--only",
        choices=list(MODES),
        help="loop just this one mode forever instead of the normal rotation - lets you preview a "
        "mode on demand instead of waiting for it to come up randomly",
    )
    parser.add_argument("--duration", type=float, default=3.0, help="seconds to run before --snapshot")
    parser.add_argument(
        "--clock-lead", type=float, default=10.0, help="seconds into each minute before switching to a fun mode"
    )
    parser.add_argument("--fun-duration", type=float, default=45.0, help="seconds each fun-mode break lasts")
    parser.add_argument("--brightness", type=int, default=30, help="real hardware only, percent 1-100")
    parser.add_argument("--gpio-slowdown", type=int, default=4, help="real hardware only")
    parser.add_argument(
        "--hardware-pulsing",
        action="store_true",
        help="real hardware only - requires the GPIO4/GPIO18 jumper to be soldered on the HAT; "
        "routes refresh timing through a hardware clock instead of software bit-banging, which "
        "removes most OS-scheduling-induced flicker",
    )
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

        display = MatrixDisplay(
            brightness=args.brightness,
            gpio_slowdown=args.gpio_slowdown,
            hardware_pulsing=args.hardware_pulsing,
        )

    if args.only:
        run_single(display, args.only)
    else:
        run_live(display, args.clock_lead, args.fun_duration)


if __name__ == "__main__":
    main()
