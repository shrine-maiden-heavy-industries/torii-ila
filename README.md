# Torii ILA

> [!WARNING]
> Torii ILA is in early development, it may not be stable, or even functional at all, use at your own risk.

Torii ILA is an Integrated Logic Analyzer (ILA) for [Torii] based designs, it is adapted from the ILA that is a part of [SOL] and aims to be more generally useful outside of it, and also
aims to replace it directly.

It provides several backhaul interfaces for getting the ILA samples off of the device and on to a host:

* USB - Using [SOL]
* UART - Using [`torii.lib.serial`]

## License

Torii ILA is licensed under the [BSD-3-Clause], the full text of which can be found in the [`LICENSE`] file.

[Torii]: https://github.com/shrine-maiden-heavy-industries/torii-hdl/
[SOL]: https://github.com/shrine-maiden-heavy-industries/sol/
[`torii.lib.serial`]: https://github.com/shrine-maiden-heavy-industries/torii-hdl/blob/main/torii/lib/stdio/serial.py
[BSD-3-Clause]: https://spdx.org/licenses/BSD-3-Clause.html
[`LICENSE`]: ./LICENSE
