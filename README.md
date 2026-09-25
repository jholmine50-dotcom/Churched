# Churched

PREACH FLOW — apresentação com espelho PC ↔ celular (o PC toca o áudio, o celular controla).

## Como usar

1. **PC:** abra `https://jholmine50-dotcom.github.io/Churched/palco.html` (ou o arquivo `PREACH_FLOW_V10_ESPELHO.html`) e clique em **ESPELHAR** — anote o **código da sala**.
2. **Celular:** abra o site abaixo, digite o código e toque em **ENTRAR NA SALA**.
3. No celular aparece o CONTROLE (TOCAR, STOP, intensidade, fala, faixas); o PC executa e o áudio sai dele.

## Site (GitHub Pages)

`https://jholmine50-dotcom.github.io/Churched/`

- **`palco.html`** — o palco no navegador, com som (baixa as faixas de `audio/`).
- **`espelho/PREACH_ESPELHO.html`** — controle (36 KB), leve, roda em qualquer celular.
- **`index.html`** — porta de entrada: digite o código e vai direto pro controle.
- Ativado em **Settings → Pages → Deploy from a branch → `main` → `/ (root)`** (workflow `.github/workflows/pages.yml`).

## Arquivo grande

O `PREACH_FLOW_V10_ESPELHO.html` tem **227 MB** e **não cabe no GitHub** (limite de 100 MB por arquivo).
Hospede-o separadamente (EdgeOne, servidor próprio ou rode direto no PC com duplo clique).

## Regras do repositório

Só código — com **uma exceção**: `audio/` (as 28 faixas que o `palco.html` toca, 170 MB). Mídia de trabalho (wav, masters), HTMLs gigantes, logs e chaves de API ficam de fora — ver `.gitignore`.
