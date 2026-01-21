<?xml version="1.0" encoding="UTF-8"?>
<xsl:stylesheet version="1.0"
    xmlns:xsl="http://www.w3.org/1999/XSL/Transform">

    <xsl:output method="html" indent="yes" encoding="UTF-8"/>

    <xsl:template match="/">
        <html dir="rtl">
            <head>
                <meta charset="UTF-8"/>

                <style>
          body {
            font-family: serif;
            line-height: 1.8;
          }
          .node {
            padding: 2px 4px;
            margin: 2px;
            display: inline-block;
          }
                </style>

                <script>
        (function () {
          function randomColor(i) {
            var hue = (i * 137.508) % 360;
            return "hsl(" + hue + ",70%,85%)";
          }

          document.addEventListener("DOMContentLoaded", function () {
            var elements = document.querySelectorAll(".node");
            var style = document.createElement("style");
            document.head.appendChild(style);

            elements.forEach(function (el, i) {
              var className = "xml_el_" + i;
              var color = randomColor(i);

              style.sheet.insertRule(
                "." + className + " { background-color: " + color + "; }",
                style.sheet.cssRules.length
              );

              el.classList.add(className);

              window[className] = {
                element: el,
                color: color
              };
            });
          });
        })();
                </script>

            </head>
            <body>
                <xsl:apply-templates/>
            </body>
        </html>
    </xsl:template>

    <xsl:template match="*">
        <div class="node">
            <strong>
                <xsl:value-of select="name()"/>
            </strong>
            <xsl:text>: </xsl:text>
            <xsl:apply-templates/>
        </div>
    </xsl:template>

    <xsl:template match="text()">
        <span>
            <xsl:value-of select="."/>
        </span>
    </xsl:template>

</xsl:stylesheet>
