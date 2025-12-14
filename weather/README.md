# Previsão — Ponta Grossa, PR

Pequeno site estático em `/weather` que consulta Open-Meteo e mostra previsão para Ponta Grossa (lat -25.0905, lon -50.1638).

Como testar localmente:

```bash
# a partir da raiz do repositório
python3 -m http.server 8000
# abrir http://localhost:8000/weather/
```

Recursos adicionados:
- Ícones SVG em `/weather/icons`
- Alternador de tema (`Claro/Escuro`) salvo em `localStorage` (botão no canto superior)
- Workflow GitHub Actions para publicar o conteúdo de `/weather` no GitHub Pages automaticamente (veja `.github/workflows/deploy_weather.yml`).

Deploy via GitHub Pages (automático):
- O workflow publica o conteúdo da pasta `/weather` usando as Actions `upload-pages-artifact` e `deploy-pages`.
- Depois do primeiro push, vá em *Settings → Pages* para verificar o status caso necessário.

Se preferir eu ajusto o tema, ícones ou o conteúdo do workflow (ex.: publicar em branch `gh-pages` em vez de Pages app integrada).