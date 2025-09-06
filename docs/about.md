# About project

This library provides trajectory calculation for ballistic projectiles launched by airguns, bows, firearms, artillery, etc.

The core point-mass (3DoF) ballistic model underlying this project was used on the earliest digital computers.  Notable implementations that preceded this one:

* Robert McCoy (author of *Modern Exterior Ballistics*) implemented one in BASIC.
* [JBM published code in C](https://www.jbmballistics.com/ballistics/downloads/downloads.shtml).
* Nikolay Gekht ported that to [C#](https://gehtsoft-usa.github.io/BallisticCalculator/web-content.html), extended it with formulas from Bryan Litz's _Applied Ballistics_, and ported it to [Go](https://godoc.org/github.com/gehtsoft-usa/go_ballisticcalc).
* Alexandre Trofimov implemented a calculator in [JavaScript](https://ptosis.ch/ebalka/ebalka.html).

This Python3 implementation has been expanded to support multiple ballistic coefficients and custom drag functions, such as those derived from Doppler radar data.

!!! note "RISK NOTICE"
    
    The library performs very limited simulation of a complex physical process and so it performs a lot of approximations. Therefore, the calculation results MUST NOT be considered as completely and reliably reflecting actual behavior or characteristics of projectiles. While these results may be used for educational purpose, they must NOT be considered as reliable for the areas where incorrect calculation may cause making a wrong decision, financial harm, or can put a human life at risk.
    
    THE CODE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE MATERIALS OR THE USE OR OTHER DEALINGS IN THE MATERIALS.
