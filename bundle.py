import os

with open('simulation/index.html', 'r', encoding='utf-8') as f:
    html = f.read()

with open('simulation/style.css', 'r', encoding='utf-8') as f:
    css = f.read()

with open('simulation/app.js', 'r', encoding='utf-8') as f:
    js = f.read()

html = html.replace('<link rel="stylesheet" href="style.css">', f'<style>\n{css}\n</style>')
html = html.replace('<script src="app.js"></script>', f'<script>\n{js}\n</script>')

with open('Dar_Traffic_Simulation.html', 'w', encoding='utf-8') as f:
    f.write(html)

print('Done!')
