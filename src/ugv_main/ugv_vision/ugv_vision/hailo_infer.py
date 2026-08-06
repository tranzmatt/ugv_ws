"""Thin synchronous wrapper around the HailoRT Python API for single-frame inference.

hailo_platform lives in a separate venv (/home/ws/HailoAi/venv), not in any apt or
pip-installed location system Python can see. Rather than pip-installing the vendor
wheel system-wide (which needs --break-system-packages under PEP 668), this module
borrows that venv's site-packages via sys.path — both are the same Python 3.12 ABI,
so the compiled hailo_platform extension loads cleanly either way.
"""

import sys


def _ensure_hailo_platform_importable(venv_site_packages):
    if 'hailo_platform' in sys.modules:
        return
    try:
        import hailo_platform  # noqa: F401
        return
    except ImportError:
        pass
    if venv_site_packages not in sys.path:
        sys.path.insert(0, venv_site_packages)


class HailoDetector:
    """Runs a single HEF (compiled with on-chip NMS) synchronously, one frame at a time."""

    def __init__(self, hef_path, venv_site_packages, timeout_ms=5000):
        _ensure_hailo_platform_importable(venv_site_packages)
        import hailo_platform as hp

        self._timeout_ms = timeout_ms

        params = hp.VDevice.create_params()
        # Round-robin + shared group lets HailoRT's scheduler activate the model's
        # streams on demand; calling run_async() without this raises
        # HAILO_STREAM_NOT_ACTIVATED.
        params.scheduling_algorithm = hp.HailoSchedulingAlgorithm.ROUND_ROBIN
        params.group_id = 'SHARED'
        self._vdevice = hp.VDevice(params)

        self._infer_model = self._vdevice.create_infer_model(hef_path)
        self._infer_model.set_batch_size(1)
        self._output_name = self._infer_model.outputs[0].name
        self._output_shape = self._infer_model.output(self._output_name).shape

        input_shape = self._infer_model.input().shape
        self.input_height, self.input_width = input_shape[0], input_shape[1]

        self._config_ctx = self._infer_model.configure()
        self._configured_model = self._config_ctx.__enter__()

    def infer(self, frame_uint8_rgb):
        """frame_uint8_rgb: HxWx3 uint8 array already resized to (input_height, input_width).

        Returns a list of per-class numpy arrays of shape (N, 5): [x1, y1, x2, y2, score],
        with box coordinates normalized to [0, 1].
        """
        import numpy as np

        output_buffer = np.empty(self._output_shape, dtype=np.float32)
        bindings = self._configured_model.create_bindings(
            output_buffers={self._output_name: output_buffer})
        bindings.input().set_buffer(frame_uint8_rgb)

        self._configured_model.wait_for_async_ready(timeout_ms=self._timeout_ms)
        job = self._configured_model.run_async([bindings])
        job.wait(self._timeout_ms)

        return bindings.output().get_buffer()

    def close(self):
        if self._config_ctx is not None:
            self._config_ctx.__exit__(None, None, None)
            self._config_ctx = None
        self._vdevice.release()
