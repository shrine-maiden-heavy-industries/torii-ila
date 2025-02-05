```{toctree}
:hidden:

install
getting_started

ila/index
backhaul/index

internal
changelog
license

Torii <https://torii.shmdn.link>
Source Code <https://github.com/shrine-maiden-heavy-industries/torii-ila/>
```

# Torii ILA

```{warning}
   This manual is a work in progress and is seriously incomplete!
```

The Torii Integrated Logic Analyzer (ILA) allows for the introspection into a [Torii] based FPGA design that is running on real hardware.

## Whats in the box?

There are two primary ILA implementations that are available for use:

* {py:class}`UARTIntegratedLogicAnalyzer <torii_ila.uart.UARTIntegratedLogicAnalyzer>`
* {py:class}`USBIntegratedLogicAnalyzer <torii_ila.usb.USBIntegratedLogicAnalyzer>`

The simplest one is the {py:class}`UARTIntegratedLogicAnalyzer <torii_ila.uart.UARTIntegratedLogicAnalyzer>`, it provides the ILA samples over a simple unidirectional UART stream. The {py:class}`USBIntegratedLogicAnalyzer <torii_ila.usb.USBIntegratedLogicAnalyzer>` is a touch more complex, however it provides the ILA samples over a USB bulk endpoint, which may be more ergonomic to work with, depending on the device.

## Installation and Getting Started

To get set up with Torii ILA, follow the [installation instructions], and then head over to the [getting started] page for examples of both the USB and UART ILAs.

## License

Torii ILA is licensed under the [BSD-3-Clause], the full text of which can be found in the [`LICENSE`] file.

[Torii]: https://torii.shmdn.link
[installation instructions]: ./install.md
[getting started]: ./getting_started.md
[BSD-3-Clause]: https://spdx.org/licenses/BSD-3-Clause.html
[`LICENSE`]: ./license.md
