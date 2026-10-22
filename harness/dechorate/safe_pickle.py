"""Load dEchorate_echo_notes.pkl without running arbitrary code: only numpy's array rebuild and dtype are allowed."""
import pickle

import numpy as np

ALLOWED = {('numpy.core.numeric', '_frombuffer'), ('numpy._core.numeric', '_frombuffer'), ('numpy', 'dtype')}


class _Restricted(pickle.Unpickler):
    def find_class(self, module, name):
        if (module, name) not in ALLOWED:
            raise pickle.UnpicklingError(f'refusing {module}.{name}')
        if name == 'dtype':
            return np.dtype
        from numpy._core import numeric
        return numeric._frombuffer


def load_echo_notes(path):
    with open(path, 'rb') as fh:
        return _Restricted(fh).load()
