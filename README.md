# Torii ILA

> [!WARNING]
> Torii ILA is in early development, it may not be stable, or even functional at all, use at your own risk.

Torii ILA is an Integrated Logic Analyzer (ILA) for [Torii] based designs, it is adapted from the ILA that is a part of [SOL] and aims to be more generally useful outside of it, and also
aims to replace it directly.

It provides several backhaul interfaces for getting the ILA samples off of the device and on to a host:

* [USB] - Using [Torii-USB]
* [UART] - Using [`torii.lib.serial`]

## Getting Started

To get started, see the [installation] instructions and [Getting Started] sections of the [Documentation].

## Community

The two primary community spots for Torii and by extension Torii ILA are the `#torii` IRC channel on [libera.chat] (`irc.libera.chat:6697`) which you can join via your favorite IRC client or the [web chat], and the [discussion forum] on GitHub.

Please do join and share your projects using Torii, ask questions, get help with problems, or discuss development.

## License

Torii ILA is licensed under the [BSD-3-Clause], the full text of which can be found in the [`LICENSE`] file.

The documentation is licensed under the Creative Commons [CC-BY-SA 4.0] and can be found in the [`LICENSE.docs`] file

[Torii]: https://github.com/shrine-maiden-heavy-industries/torii-hdl/
[Torii-USB]: https://github.com/shrine-maiden-heavy-industries/torii-usb/
[SOL]: https://github.com/shrine-maiden-heavy-industries/sol/
[`torii.lib.serial`]: https://github.com/shrine-maiden-heavy-industries/torii-hdl/blob/main/torii/lib/stdio/serial.py
[installation]: https://torii-ila.shmdn.link/install.html
[Getting Started]: https://torii-ila.shmdn.link/getting_started.html
[Documentation]: https://torii-ila.shmdn.link
[USB]: https://torii-ila.shmdn.link/ila/usb.html
[UART]: https://torii-ila.shmdn.link/ila/uart.html
[libera.chat]: https://libera.chat/
[web chat]: https://web.libera.chat/#torii
[discussion forum]: https://github.com/shrine-maiden-heavy-industries/torii-ila/discussions
[BSD-3-Clause]: https://spdx.org/licenses/BSD-3-Clause.html
[`LICENSE`]: ./LICENSE
[CC-BY-SA 4.0]: https://creativecommons.org/licenses/by-sa/4.0/
[`LICENSE.docs`]: ./LICENSE.docs
