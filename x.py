from bs4 import BeautifulSoup


string = """<pre class="overflow-visible! px-0!" data-start="552" data-end="619"><div class="contain-inline-size rounded-2xl corner-superellipse/1.1 relative bg-token-sidebar-surface-primary"><div class="flex items-center text-token-text-secondary px-4 py-2 text-xs font-sans justify-between h-9 bg-token-sidebar-surface-primary select-none rounded-t-2xl corner-t-superellipse/1.1">python</div><div class="sticky top-[calc(--spacing(9)+var(--header-height))] @w-xl/main:top-9"><div class="absolute end-0 bottom-0 flex h-9 items-center pe-2"><div class="bg-token-bg-elevated-secondary text-token-text-secondary flex items-center gap-4 rounded-sm px-2 font-sans text-xs"><button class="flex gap-1 items-center select-none py-1" aria-label="Kopieren"><svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" aria-hidden="true" class="icon-sm"><use href="/cdn/assets/sprites-core-k5zux585.svg#ce3544" fill="currentColor"></use></svg>Code kopieren</button></div></div></div><div class="overflow-y-auto p-4" dir="ltr"><code class="whitespace-pre! language-python"><span><span>center_x = </span><span><span class="hljs-built_in">int</span></span><span>(bbox[</span><span><span class="hljs-number">0</span></span><span>][</span><span><span class="hljs-number">0</span></span><span>])
center_y = </span><span><span class="hljs-built_in">int</span></span><span>(bbox[</span><span><span class="hljs-number">0</span></span><span>][</span><span><span class="hljs-number">1</span></span><span>])
</span></span></code></div></div></pre>"""

# 7. HTML aus Zwischenablage holen

# 8. BeautifulSoup Extraktion
soup = BeautifulSoup(string, "html.parser")
clean_code = soup.get_text()
print(clean_code)
