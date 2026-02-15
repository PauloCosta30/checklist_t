# 💥 ERRO DE PREÇO BOT

Bot Telegram que monitora automaticamente erros de preço em **iPhone, Apple Watch, Garmin, Perfumes, Maquiagem, Polo e Roupas Masculinas** — alertando você em tempo real.

---

## 📁 Estrutura do Projeto

```
errobot/
├── main.py              ← Entrypoint (Render inicia por aqui)
├── bot.py               ← Comandos e scheduler do Telegram
├── monitor.py           ← Orquestrador de todas as buscas
├── config.py            ← Variáveis de ambiente
├── keep_alive.py        ← Servidor HTTP (mantém Render acordado)
├── requirements.txt     ← Dependências Python
├── render.yaml          ← Config do Render
└── scrapers/
    ├── mercadolivre.py  ← Scraper ML (API oficial)
    └── amazon.py        ← Scraper Amazon BR (HTML)
```

---

## 🚀 PASSO A PASSO — Deploy no Render

### 1. Criar o Bot no Telegram

1. Abra o Telegram e busque **@BotFather**
2. Envie `/newbot`
3. Dê um nome: `Erro de Preço Bot`
4. Dê um username: `ErroDePrecoBot` (deve terminar em `bot`)
5. Copie o **TOKEN** gerado (ex: `7123456789:AAF...`)

### 2. Pegar seu Chat ID

**Opção A — Grupo/Canal:**
1. Crie um grupo ou canal no Telegram
2. Adicione o seu bot como administrador
3. Envie uma mensagem no grupo
4. Acesse: `https://api.telegram.org/bot<SEU_TOKEN>/getUpdates`
5. Copie o `chat.id` (começa com `-` para grupos, ex: `-1001234567890`)

**Opção B — Chat direto:**
1. Busque **@userinfobot** no Telegram
2. Envie `/start` — ele retorna seu ID pessoal

### 3. Subir no GitHub

```bash
# Na pasta do projeto:
git init
git add .
git commit -m "💥 Erro de Preço Bot — initial commit"
git remote add origin https://github.com/SEU_USUARIO/erro-de-preco-bot.git
git push -u origin main
```

### 4. Deploy no Render

1. Acesse [render.com](https://render.com) e faça login
2. Clique em **New → Web Service**
3. Conecte seu repositório GitHub
4. Configure:
   - **Name:** `erro-de-preco-bot`
   - **Environment:** `Python 3`
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `python main.py`
   - **Plan:** Free

5. Vá em **Environment** e adicione as variáveis:

| Variável | Valor |
|---|---|
| `TELEGRAM_TOKEN` | `7123456789:AAF...` |
| `TELEGRAM_CHAT_ID` | `-1001234567890` |
| `SCAN_INTERVAL_MINUTES` | `15` |
| `DESCONTO_MINIMO_PORCENTO` | `40` |

6. Clique em **Create Web Service**

✅ O Render vai instalar as dependências e iniciar o bot!

---

## ⚙️ Variáveis de Ambiente

| Variável | Descrição | Padrão |
|---|---|---|
| `TELEGRAM_TOKEN` | Token do bot (BotFather) | **obrigatório** |
| `TELEGRAM_CHAT_ID` | ID do grupo/canal/chat | **obrigatório** |
| `SCAN_INTERVAL_MINUTES` | Intervalo entre scans | `15` |
| `DESCONTO_MINIMO_PORCENTO` | % mínimo para alertar | `40` |
| `PRECO_MAX_IPHONE` | Preço máx. iPhone (R$) | `6000` |
| `PRECO_MAX_APPLEWATCH` | Preço máx. Apple Watch (R$) | `3000` |
| `PRECO_MAX_GARMIN` | Preço máx. Garmin (R$) | `2500` |
| `PRECO_MAX_PERFUME` | Preço máx. Perfume (R$) | `800` |
| `PRECO_MAX_MAQUIAGEM` | Preço máx. Maquiagem (R$) | `500` |
| `PRECO_MAX_POLO` | Preço máx. Polo (R$) | `300` |
| `PRECO_MAX_ROUPA` | Preço máx. Roupa (R$) | `500` |

---

## 📲 Comandos do Bot

| Comando | Descrição |
|---|---|
| `/start` | Boas-vindas e categorias |
| `/status` | Status do monitoramento |
| `/categorias` | Lista categorias ativas |
| `/ping` | Testa se o bot está online |

---

## 🛒 Lojas Monitoradas

- **Mercado Livre** (via API oficial)
- **Amazon Brasil** (via scraping HTML)

> 💡 Para adicionar mais lojas, crie um novo arquivo em `scrapers/` seguindo o mesmo padrão de `mercadolivre.py` ou `amazon.py`, e registre-o no `monitor.py`.

---

## 💡 Dicas

- **Render Free hiberna** serviços após 15min sem requisições. O `keep_alive.py` resolve isso internamente, mas use um serviço como [UptimeRobot](https://uptimerobot.com) para fazer ping no seu URL a cada 5 minutos como camada extra.
- O bot usa **deduplicação** — o mesmo produto não é alertado duas vezes.
- Ajuste `DESCONTO_MINIMO_PORCENTO` conforme sua necessidade (40% é conservador; 60%+ garante apenas erros reais).

---

## 📜 Licença

MIT — use à vontade, mas não nos culpe por erros corrigidos antes de você comprar 😂
