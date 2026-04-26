"""Run Quantum ESPRESSO calculations as background subprocesses."""

import os
import subprocess
import threading
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import QE_BIN


class QERunner:
    """
    Manages a single QE calculation subprocess.

    Usage:
        runner = QERunner(calc_dir, input_file, output_file,
                          executable='pw.x', nproc=1)
        runner.start(on_line=callback, on_finish=callback)
        runner.stop()
    """

    def __init__(self, calc_dir, input_file, output_file,
                 executable='pw.x', nproc=1, mpirun=None):
        self.calc_dir = calc_dir
        self.input_file = input_file
        self.output_file = output_file
        self.executable = executable
        self.nproc = nproc
        self.mpirun = mpirun
        self._process = None
        self._thread = None
        self.running = False
        self._on_line = None
        self._on_finish = None

    # ------------------------------------------------------------------
    def _build_cmd(self):
        exe = os.path.join(QE_BIN, self.executable)
        if not os.path.isfile(exe):
            # Fall back to PATH
            exe = self.executable

        mpirun_bin = self.mpirun or shutil.which('mpirun') or shutil.which('mpiexec')
        if mpirun_bin and self.nproc > 1:
            cmd = [mpirun_bin, '-np', str(self.nproc), exe]
        else:
            cmd = [exe]
        cmd += ['-in', os.path.basename(self.input_file)]
        return cmd

    # ------------------------------------------------------------------
    def start(self, on_line=None, on_finish=None):
        if self.running:
            return False
        self._on_line = on_line
        self._on_finish = on_finish
        os.makedirs(self.calc_dir, exist_ok=True)
        cmd = self._build_cmd()
        try:
            self._process = subprocess.Popen(
                cmd,
                cwd=self.calc_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except FileNotFoundError as e:
            if on_finish:
                on_finish(returncode=-1, error=str(e))
            return False

        self.running = True
        self._thread = threading.Thread(target=self._stream, daemon=True)
        self._thread.start()
        return True

    # ------------------------------------------------------------------
    def _stream(self):
        outpath = os.path.join(self.calc_dir, self.output_file)
        with open(outpath, 'w') as fout:
            for line in self._process.stdout:
                fout.write(line)
                fout.flush()
                if self._on_line:
                    self._on_line(line)
        self._process.wait()
        self.running = False
        if self._on_finish:
            self._on_finish(returncode=self._process.returncode, error=None)

    # ------------------------------------------------------------------
    def stop(self):
        if self._process and self.running:
            self._process.terminate()
            self.running = False

    # ------------------------------------------------------------------
    @property
    def pid(self):
        return self._process.pid if self._process else None


class PPRunner(QERunner):
    """Runner preset for bands.x, dos.x, projwfc.x, pp.x, etc."""

    def __init__(self, calc_dir, input_file, output_file, executable, nproc=1):
        super().__init__(calc_dir, input_file, output_file,
                         executable=executable, nproc=nproc)
