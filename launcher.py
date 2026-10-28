"""Punto de entrada del ejecutable (PyInstaller). Sin argumentos abre la app."""
import sys

from rsa.__main__ import main

if __name__ == "__main__":
    main(sys.argv[1:] or ["app"])
