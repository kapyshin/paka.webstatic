## `cssmin.py` - A Python port of the YUI CSS compressor.

## Copyright (c) 2010 Zachary Voase

## Permission is hereby granted, free of charge, to any person
## obtaining a copy of this software and associated documentation
## files (the "Software"), to deal in the Software without
## restriction, including without limitation the rights to use,
## copy, modify, merge, publish, distribute, sublicense, and/or sell
## copies of the Software, and to permit persons to whom the
## Software is furnished to do so, subject to the following
## conditions:

## The above copyright notice and this permission notice shall be
## included in all copies or substantial portions of the Software.

## THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
## EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES
## OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
## NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
## HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
## WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING
## FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
## OTHER DEALINGS IN THE SOFTWARE.

## -------------------------------------------------------------------------------

## This software contains portions of the YUI CSS Compressor, notably some regular
## expressions for reducing the size of CSS. The YUI Compressor source code can be
## found at <http://github.com/yui/yuicompressor>, and is licensed as follows:

## > YUI Compressor Copyright License Agreement (BSD License)
## > 
## > Copyright (c) 2009, Yahoo! Inc.
## > All rights reserved.
## > 
## > Redistribution and use of this software in source and binary forms,
## > with or without modification, are permitted provided that the following
## > conditions are met:
## > 
## > * Redistributions of source code must retain the above
## >   copyright notice, this list of conditions and the
## >   following disclaimer.
## > 
## > * Redistributions in binary form must reproduce the above
## >   copyright notice, this list of conditions and the
## >   following disclaimer in the documentation and/or other
## >   materials provided with the distribution.
## > 
## > * Neither the name of Yahoo! Inc. nor the names of its
## >   contributors may be used to endorse or promote products
## >   derived from this software without specific prior
## >   written permission of Yahoo! Inc.
## > 
## > THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
## > AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
## > IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
## > DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE
## > FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
## > DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
## > SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
## > CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
## > OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
## > OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

"""`cssmin` - A Python port of the YUI CSS compressor."""


import re
import sys
from io import StringIO


__version__ = '0.1.5'


def remove_comments(css):
    """Remove all CSS comment blocks."""
    
    iemac = False
    preserve = False
    comment_start = css.find("/*")
    while comment_start >= 0:
        # Preserve comments that look like `/*!...*/`.
        # Slicing is used to make sure we don"t get an IndexError.
        preserve = css[comment_start + 2:comment_start + 3] == "!"
        
        comment_end = css.find("*/", comment_start + 2)
        if comment_end < 0:
            if not preserve:
                css = css[:comment_start]
                break
        elif comment_end >= (comment_start + 2):
            if css[comment_end - 1] == "\\":
                # This is an IE Mac-specific comment; leave this one and the
                # following one alone.
                comment_start = comment_end + 2
                iemac = True
            elif iemac:
                comment_start = comment_end + 2
                iemac = False
            elif not preserve:
                css = css[:comment_start] + css[comment_end + 2:]
            else:
                comment_start = comment_end + 2
        comment_start = css.find("/*", comment_start)
    
    return css


def remove_unnecessary_whitespace(css):
    """Remove unnecessary whitespace characters."""
    
    def pseudoclasscolon(css):
        
        """
        Prevents 'p :link' from becoming 'p:link'.
        
        Translates 'p :link' into 'p ___PSEUDOCLASSCOLON___link'; this is
        translated back again later.
        """
        
        regex = re.compile(r"(^|\})(([^\{\:])+\:)+([^\{]*\{)")
        match = regex.search(css)
        while match:
            css = ''.join([
                css[:match.start()],
                match.group().replace(":", "___PSEUDOCLASSCOLON___"),
                css[match.end():]])
            match = regex.search(css)
        return css
    
    css = pseudoclasscolon(css)
    # Remove spaces from before things.
    css = re.sub(r"\s+([!{};:>+\(\)\],])", r"\1", css)
    
    # If there is a `@charset`, then only allow one, and move to the beginning.
    css = re.sub(r"^(.*)(@charset \"[^\"]*\";)", r"\2\1", css)
    css = re.sub(r"^(\s*@charset [^;]+;\s*)+", r"\1", css)
    
    # Put the space back in for a few cases, such as `@media screen` and
    # `(-webkit-min-device-pixel-ratio:0)`.
    css = re.sub(r"\band\(", "and (", css)
    
    # Put the colons back.
    css = css.replace('___PSEUDOCLASSCOLON___', ':')
    
    # Remove spaces from after things.
    css = re.sub(r"([!{}:;>+\(\[,])\s+", r"\1", css)
    
    return css


def remove_unnecessary_semicolons(css):
    """Remove unnecessary semicolons."""
    
    return re.sub(r";+\}", "}", css)


def remove_empty_rules(css):
    """Remove empty rules."""
    
    return re.sub(r"[^\}\{]+\{\}", "", css)


def normalize_rgb_colors_to_hex(css):
    """Convert `rgb(51,102,153)` to `#336699`."""
    
    regex = re.compile(r"rgb\s*\(\s*([0-9,\s]+)\s*\)")
    match = regex.search(css)
    while match:
        colors = map(lambda s: s.strip(), match.group(1).split(","))
        hexcolor = '#%.2x%.2x%.2x' % tuple(map(int, colors))
        css = css.replace(match.group(), hexcolor)
        match = regex.search(css)
    return css


def condense_zero_units(css):
    """Replace `0(px, em, %, etc)` with `0`."""
    
    return re.sub(r"([\s:])(0)(px|em|%|in|cm|mm|pc|pt|ex)", r"\1\2", css)


def condense_multidimensional_zeros(css):
    """Replace `:0 0 0 0;`, `:0 0 0;` etc. with `:0;`."""
    
    css = css.replace(":0 0 0 0;", ":0;")
    css = css.replace(":0 0 0;", ":0;")
    css = css.replace(":0 0;", ":0;")
    
    # Revert `background-position:0;` to the valid `background-position:0 0;`.
    css = css.replace("background-position:0;", "background-position:0 0;")
    
    return css


def condense_floating_points(css):
    """Replace `0.6` with `.6` where possible."""
    
    return re.sub(r"(:|\s)0+\.(\d+)", r"\1.\2", css)


def condense_hex_colors(css):
    """Shorten colors from #AABBCC to #ABC where possible."""
    
    regex = re.compile(r"([^\"'=\s])(\s*)#([0-9a-fA-F])([0-9a-fA-F])([0-9a-fA-F])([0-9a-fA-F])([0-9a-fA-F])([0-9a-fA-F])")
    match = regex.search(css)
    while match:
        first = match.group(3) + match.group(5) + match.group(7)
        second = match.group(4) + match.group(6) + match.group(8)
        if first.lower() == second.lower():
            css = css.replace(match.group(), match.group(1) + match.group(2) + '#' + first)
            match = regex.search(css, match.end() - 3)
        else:
            match = regex.search(css, match.end())
    return css


def condense_whitespace(css):
    """Condense multiple adjacent whitespace characters into one."""
    
    return re.sub(r"\s+", " ", css)


def condense_semicolons(css):
    """Condense multiple adjacent semicolon characters into one."""
    
    return re.sub(r";;+", ";", css)


def wrap_css_lines(css, line_length):
    """Wrap the lines of the given CSS to an approximate length."""
    
    lines = []
    line_start = 0
    for i, char in enumerate(css):
        # It's safe to break after `}` characters.
        if char == '}' and (i - line_start >= line_length):
            lines.append(css[line_start:i + 1])
            line_start = i + 1
    
    if line_start < len(css):
        lines.append(css[line_start:])
    return '\n'.join(lines)


def cssmin(css, wrap=None):
    css = remove_comments(css)
    css = condense_whitespace(css)
    # A pseudo class for the Box Model Hack
    # (see http://tantek.com/CSS/Examples/boxmodelhack.html)
    css = css.replace('"\\"}\\""', "___PSEUDOCLASSBMH___")
    css = remove_unnecessary_whitespace(css)
    css = remove_unnecessary_semicolons(css)
    css = condense_zero_units(css)
    css = condense_multidimensional_zeros(css)
    css = condense_floating_points(css)
    css = normalize_rgb_colors_to_hex(css)
    css = condense_hex_colors(css)
    if wrap is not None:
        css = wrap_css_lines(css, wrap)
    css = css.replace("___PSEUDOCLASSBMH___", '"\\"}\\""')
    css = condense_semicolons(css)
    return css.strip()

