"""Measure real Qt runtime phases with isolated state; requires a macOS desktop.

CPU is process CPU seconds / wall seconds (100% = one core). RSS is sampled
using ps, not Python-only allocations. This never changes installed preferences.
"""
import argparse
import json
import os
import platform
import subprocess
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from nomzy import __version__
from nomzy.activity import CompanionEvent
from nomzy.companion import NomzyDog
from nomzy.macos_overlay import has_native_macos_windowing
from nomzy.settings import DEFAULT_SETTINGS


class MeasuredDog(NomzyDog):
    def __init__(self):
        self.counts = dict(paints=0, updates=0, masks=0, native_requests=0)
        super().__init__()

    def paintEvent(self, event):
        self.counts['paints'] += 1
        super().paintEvent(event)

    def update(self, *args):
        self.counts['updates'] += 1
        super().update(*args)

    def setMask(self, region):
        self.counts['masks'] += 1
        super().setMask(region)

    def apply_native_overlay_style(self, force=False):
        self.counts['native_requests'] += 1
        super().apply_native_overlay_style(force)


def rss_mib():
    return int(subprocess.check_output(['ps', '-o', 'rss=', '-p', str(os.getpid())], text=True)) / 1024


def cpu_seconds():
    usage = os.times()
    return usage.user + usage.system


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seconds', type=int, default=60, help='seconds per measured phase')
    parser.add_argument('--soak-seconds', type=int, default=3600)
    parser.add_argument('--output', type=Path, default=Path('build/runtime-profile.json'))
    args = parser.parse_args()
    if args.seconds < 5 or args.soak_seconds < 0:
        parser.error('Use at least 5 seconds per phase and a nonnegative soak duration.')
    app = QApplication([])
    if not has_native_macos_windowing():
        raise SystemExit('Use the native Cocoa backend on a macOS desktop.')
    report = dict(version=__version__, platform=platform.platform(), python=platform.python_version(),
                  backend=app.platformName(), phases=[], complete=False, errors=[])
    phases = [(name, args.seconds) for name in ('idle', 'walking', 'animating', 'speech', 'paused')]
    if args.soak_seconds:
        phases.append(('mixed_soak', args.soak_seconds))
    with tempfile.TemporaryDirectory(prefix='nomzy-profile-') as directory, \
         patch('nomzy.companion.load_settings', return_value=dict(DEFAULT_SETTINGS)), \
         patch('nomzy.state.get_state_path', return_value=Path(directory) / 'state.json'):
        dog = MeasuredDog()
        dog.move(dog.get_centered_position())
        dog.show()
        phase_index = -1
        started = 0
        cpu_start = 0
        counts_start = {}
        samples = []
        selected_mode = None

        def select_mode(mode):
            nonlocal selected_mode
            selected_mode = mode
            dog.transition_activity(CompanionEvent.CLOSE_MENU)
            dog.transition_activity(CompanionEvent.RESUME)
            dog.hide_message()
            dog.stop_walking()
            dog.activity.reaction_animation = None
            dog.transition_activity(CompanionEvent.ANIMATION_FINISHED, animation_name=dog.activity.animation_name)
            dog.settings.update(movement_enabled=False, speech_enabled=False)
            dog.scheduler.blink_cooldown_ms = dog.scheduler.rest_cooldown_ms = 3600000
            if mode == 'paused':
                dog.transition_activity(CompanionEvent.PAUSE)

        def maintain(mode):
            if mode == 'walking':
                dog.start_tiny_walk()
                dog.scheduler.walk_ticks_remaining = 250
            elif mode == 'animating' and (dog.activity.animation_name != 'pet' or dog.animation_player.finished):
                dog.start_reaction('pet')
            elif mode == 'speech' and not dog.message:
                dog.say_message('Hello, friend! This is the beta stability test.')
                dog.scheduler.message_ticks_remaining = 750

        def save_report():
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(json.dumps(report, indent=2) + '\n')

        def advance():
            nonlocal phase_index, started, cpu_start, counts_start, samples
            now = time.monotonic()
            if phase_index >= 0:
                name, duration = phases[phase_index]
                samples.append(rss_mib())
                if now - started < duration:
                    mode = name if name != 'mixed_soak' else phases[int((now - started) // 20) % 5][0]
                    if mode != selected_mode:
                        select_mode(mode)
                    maintain(mode)
                    return
                wall = now - started
                result = dict(name=name, wall_seconds=round(wall, 2),
                              cpu_percent=round(100 * (cpu_seconds() - cpu_start) / wall, 2),
                              rss_start_mib=round(samples[0], 2), rss_end_mib=round(samples[-1], 2),
                              rss_peak_mib=round(max(samples), 2),
                              calls={k: dog.counts[k] - counts_start[k] for k in dog.counts})
                report['phases'].append(result)
                print(json.dumps(result), flush=True)
                save_report()
            phase_index += 1
            if phase_index == len(phases):
                report['complete'] = True
                save_report()
                app.quit()
                return
            name, _ = phases[phase_index]
            select_mode(name if name != 'mixed_soak' else 'idle')
            maintain(selected_mode)
            started, cpu_start = time.monotonic(), cpu_seconds()
            counts_start = dict(dog.counts)
            samples = [rss_mib()]

        previous_hook = sys.excepthook
        def failure(kind, error, traceback):
            report['errors'].append(f'{kind.__name__}: {error}')
            save_report()
            app.quit()
            previous_hook(kind, error, traceback)
        sys.excepthook = failure
        timer = QTimer()
        timer.timeout.connect(advance)
        timer.start(1000)
        QTimer.singleShot(1000, advance)
        try:
            app.exec()
        finally:
            sys.excepthook = previous_hook
            dog.timer.stop()
            dog.position_save_timer.stop()
            dog.hide()
        if not report['complete'] or report['errors']:
            raise SystemExit('Runtime profile failed or was interrupted; inspect the report.')


if __name__ == '__main__':
    main()
