# YouTube Downloader

![Python](https://img.shields.io/badge/python-3.8%2B-3670A0?style=for-the-badge&logo=python&logoColor=ffdd54)
![YouTube](https://img.shields.io/badge/YouTube-%23FF0000.svg?style=for-the-badge&logo=YouTube&logoColor=white)
![FFmpeg](https://img.shields.io/badge/FFmpeg-007808?style=for-the-badge&logo=ffmpeg&logoColor=white)

Script Python para baixar vídeos e playlists do YouTube na maior resolução disponível, priorizando a faixa de áudio em Português (Brasil) quando presente, e mesclando as streams com `ffmpeg` sem perda de qualidade.

---

## Recursos

- **Resolução máxima** — inclui 4K e 8K quando disponíveis
- **Áudio PT-BR automático** — detecta e seleciona a faixa em português do Brasil; usa o áudio padrão automaticamente caso não encontre
- **Suporte a playlists** — baixa todos os vídeos de uma playlist, criando uma pasta com o nome dela automaticamente
- **Barra de progresso** — exibe progresso em tempo real para cada download de vídeo e áudio
- **Mesclagem sem re-encode** — usa `ffmpeg -c copy` para não perder qualidade; re-encoda para MP4 automaticamente apenas se necessário
- **Argumento de saída configurável** — defina a pasta de destino via CLI
- **Modo verbose** — exibe logs de debug para diagnóstico

---

## Requisitos

- Python 3.8+
- [ffmpeg](https://ffmpeg.org/) no PATH

---

## Instalação

```bash
# 1. Clone o repositório
git clone https://github.com/adrianoleitedasilva/youtubeDownloader.git
cd youtubeDownloader

# 2. (Opcional) Crie e ative um ambiente virtual
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate

# 3. Instale as dependências
pip install -r requirements.txt
```

### Instalar o ffmpeg

```bash
# Windows (winget)
winget install Gyan.FFmpeg

# Windows (chocolatey)
choco install ffmpeg

# macOS (Homebrew)
brew install ffmpeg

# Linux (apt)
sudo apt install ffmpeg
```

Verifique a instalação:
```bash
ffmpeg -version
```

---

## Uso

```bash
# Interativo — solicita a URL no terminal
python main.py

# Baixar um vídeo
python main.py "https://www.youtube.com/watch?v=VIDEO_ID"

# Baixar uma playlist completa
python main.py "https://www.youtube.com/playlist?list=PLxxxxxxxxxxxxxxxx"

# Definindo a pasta de destino
python main.py "https://youtu.be/VIDEO_ID" -o ./videos

# Modo verbose (logs de debug)
python main.py "https://youtu.be/VIDEO_ID" -v
```

### Opções

| Argumento | Descrição | Padrão |
|-----------|-----------|--------|
| `url` | URL do vídeo ou playlist do YouTube | *(solicitado interativamente)* |
| `-o`, `--output` | Pasta de destino dos arquivos | `downloads/` |
| `-v`, `--verbose` | Exibe logs de debug | desativado |

---

## Como funciona

### Vídeo único

1. Valida a URL informada
2. Busca o melhor stream de vídeo adaptive (maior resolução)
3. Detecta faixas de áudio em PT-BR no `playerResponse`; se não encontrar, usa o áudio padrão automaticamente
4. Exibe barra de progresso durante o download do vídeo e do áudio
5. Mescla com `ffmpeg -c copy` (sem re-encode) em `.mkv`; se falhar, re-encoda para `.mp4`
6. Remove os arquivos temporários

### Playlist

1. Detecta automaticamente se a URL é de playlist (`list=PL...`)
2. Cria uma pasta com o nome da playlist dentro do diretório de destino
3. Baixa cada vídeo individualmente com barra de progresso
4. Erros em vídeos individuais são registrados e o download continua para os demais

> **Atenção:** Playlists de Rádio/Mix do YouTube (`list=RD...`) são geradas dinamicamente pelo algoritmo e não podem ser baixadas como playlist. Nesses casos, apenas o vídeo da URL será baixado.

---

## Estrutura do projeto

```
youtubeDownloader/
├── main.py           # Script principal
├── requirements.txt  # Dependências Python
└── downloads/        # Pasta de saída (criada automaticamente, ignorada pelo git)
```

---

## Licença

Distribuído sob a licença MIT. Consulte o arquivo [LICENSE](LICENSE) para mais detalhes.
