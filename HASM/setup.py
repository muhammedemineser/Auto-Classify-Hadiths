from numpy import get_include
from setuptools import setup
from Cython.Build import cythonize

setup(
    ext_modules=cythonize("/home/mo/desk/apps/classify/HASM/diff_np_perf.pyx"),
    include_dirs=[get_include()],
)
