# Installation

```{warning}
The following instructions are a work-in-progress and may not be entirely up to date.
```

Torii ILA is as the name implies, a [Torii] library, so make sure you have [Torii installed] first and foremost. Once done you should be all set to install Torii ILA.

Depending on which [ILA Interface] you want, if any, there are some needed prerequisites.

For the [USB] based ILA and backhaul interface, you need [pyusb] and [SOL] installed, and for [UART] support you need [pyserial]. There is also a [pyvcd] dependency regardless if you want USB and or UART ILA support, but that came free with the [Torii] install.

To install Torii ILA as either [standalone](#standalone), with [USB support](#usb), with [UART support](#uart), or with [everything](#everything) simply follow the steps below.

### Standalone

```{eval-rst}
.. tab:: pypi

	.. code-block:: console

		$ pip install torii-ila

.. tab:: From Source

	.. code-block:: console

		$ pip install 'torii_ila @ git+https://github.com/shrine-maiden-heavy-industries/torii-ila.git'

```

### USB

```{eval-rst}
.. tab:: pypi

	.. code-block:: console

		$ pip install 'torii-ila[usb]'

.. tab:: From Source

	.. code-block:: console

		$ pip install 'torii_ila[usb] @ git+https://github.com/shrine-maiden-heavy-industries/torii-ila.git'

```

### UART

```{eval-rst}
.. tab:: pypi

	.. code-block:: console

		$ pip install 'torii-ila[serial]'

.. tab:: From Source

	.. code-block:: console

		$ pip install 'torii_ila[serial] @ git+https://github.com/shrine-maiden-heavy-industries/torii-ila.git'

```

### Everything

```{eval-rst}
.. tab:: pypi

	.. code-block:: console

		$ pip install 'torii-ila[usb,serial]'

.. tab:: From Source

	.. code-block:: console

		$ pip install 'torii_ila[usb,serial] @ git+https://github.com/shrine-maiden-heavy-industries/torii-ila.git'

```

From here on you can head over to [Getting Started] to see the basic usage and the examples.

[Torii]: https://github.com/shrine-maiden-heavy-industries/torii-hdl/
[Torii installed]: https://torii.shmdn.link/install.html
[ILA Interface]: ./ila/index.md
[USB]: ./ila/usb.md
[UART]: ./ila/uart.md
[pyserial]: https://github.com/pyserial/pyserial
[pyusb]: https://github.com/pyusb/pyusb
[SOL]: https://github.com/shrine-maiden-heavy-industries/sol
[pyvcd]: https://github.com/westerndigitalcorporation/pyvcd
[Getting Started]: ./getting_started.md
