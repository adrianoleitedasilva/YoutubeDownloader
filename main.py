import os
import re
import shutil
import subprocess
import json
import logging
import argparse

from pytubefix import YouTube, Playlist
from tqdm import tqdm

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
log = logging.getLogger(__name__)

YT_PATTERN = re.compile(r"(https?://)?(www\.)?(youtube\.com|youtu\.be)/.+")
PLAYLIST_PATTERN = re.compile(r"(https?://)?(www\.)?youtube\.com/(playlist\?|watch\?.+&)list=")


def slugify(text: str) -> str:
    text = re.sub(r"[^\w\s-]", "", text, flags=re.UNICODE)
    text = re.sub(r"\s+", "_", text.strip())
    return re.sub(r"_+", "_", text)


def check_ffmpeg():
    if shutil.which("ffmpeg") is None:
        raise RuntimeError("ffmpeg não encontrado no PATH. Instale e tente novamente (ffmpeg -version).")


class ProgressBar:
    def __init__(self):
        self._bar = None
        self.label = "Baixando…"

    def set_label(self, label: str):
        self.label = label

    def on_progress(self, stream, chunk, bytes_remaining):
        total = stream.filesize
        if self._bar is None:
            self._bar = tqdm(total=total, unit="B", unit_scale=True, desc=self.label[:45], leave=True)
        self._bar.n = total - bytes_remaining
        self._bar.refresh()

    def on_complete(self, stream, filepath):
        if self._bar:
            self._bar.n = self._bar.total
            self._bar.refresh()
            self._bar.close()
            self._bar = None


def achar_itag_audio_ptbr(yt: YouTube):
    info = yt.vid_info
    if isinstance(info, str):
        info = json.loads(info)

    pr = info.get("playerResponse") or info.get("player_response") or info
    sd = (pr or {}).get("streamingData", {})
    adaptive = sd.get("adaptiveFormats", [])

    candidatos = []
    for f in adaptive:
        if "audio" in (f.get("mimeType") or ""):
            at = f.get("audioTrack", {}) or {}
            label = " ".join([
                str(at.get("displayName", "")),
                str(at.get("id", "")),
                str(at.get("audioIsDefault", ""))
            ]).lower()
            if ("portugu" in label) or ("pt" in at.get("id", "").lower()) or ("pt-br" in label) or ("brasil" in label):
                br = f.get("averageBitrate") or f.get("bitrate") or 0
                itag = f.get("itag")
                if itag is not None:
                    candidatos.append((itag, int(br)))

    if not candidatos:
        return None
    candidatos.sort(key=lambda x: x[1], reverse=True)
    return candidatos[0][0]


def baixar_video(url: str, pasta_destino: str = "downloads"):
    if not YT_PATTERN.match(url):
        raise ValueError(f"URL inválida: {url}")

    check_ffmpeg()
    os.makedirs(pasta_destino, exist_ok=True)

    pb = ProgressBar()
    yt = YouTube(url, on_progress_callback=pb.on_progress, on_complete_callback=pb.on_complete)
    titulo = slugify(yt.title)
    log.info("Título: %s", yt.title)
    log.info("Canal:  %s", yt.author)

    video_best = yt.streams.filter(adaptive=True, type="video").order_by("resolution").desc().first()

    if not video_best:
        prog = yt.streams.filter(progressive=True, file_extension="mp4").order_by("resolution").desc().first()
        if not prog:
            raise RuntimeError("Não encontrei stream de vídeo.")
        saida = os.path.join(pasta_destino, f"{titulo}.mp4")
        pb.set_label(f"Vídeo: {titulo[:35]}")
        log.info("Nada de adaptive. Baixando progressivo %s…", prog.resolution)
        prog.download(output_path=pasta_destino, filename=os.path.basename(saida))
        log.info("Concluído: %s", saida)
        return

    itag_pt = achar_itag_audio_ptbr(yt)

    if itag_pt is None:
        log.warning("Faixa PT-BR não encontrada. Usando áudio padrão.")
        audio_best = yt.streams.filter(adaptive=True, type="audio").order_by("abr").desc().first()
    else:
        audio_best = yt.streams.get_by_itag(itag_pt)
        if not audio_best:
            audio_best = yt.streams.filter(adaptive=True, type="audio").order_by("abr").desc().first()

    if not audio_best:
        raise RuntimeError("Não encontrei faixa de áudio para baixar.")

    v_ext = os.path.splitext(video_best.default_filename)[1] or ".mp4"
    a_ext = os.path.splitext(audio_best.default_filename)[1] or ".m4a"
    video_tmp = os.path.join(pasta_destino, f"{titulo}.video{v_ext}")
    audio_tmp = os.path.join(pasta_destino, f"{titulo}.audio{a_ext}")

    pb.set_label(f"[Vídeo] {titulo[:38]}")
    log.info("Baixando VÍDEO em %s…", video_best.resolution)
    video_best.download(output_path=pasta_destino, filename=os.path.basename(video_tmp))

    idioma_msg = "PT-BR" if itag_pt is not None else "padrão"
    pb.set_label(f"[Áudio {idioma_msg}] {titulo[:32]}")
    log.info("Baixando ÁUDIO (%s)…", idioma_msg)
    audio_best.download(output_path=pasta_destino, filename=os.path.basename(audio_tmp))

    saida = os.path.join(pasta_destino, f"{titulo}.mkv")
    log.info("Mesclando com ffmpeg (sem re-encode)…")
    cmd_copy = ["ffmpeg", "-y", "-i", video_tmp, "-i", audio_tmp, "-c", "copy", "-movflags", "+faststart", saida]
    result = subprocess.run(cmd_copy, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

    if result.returncode != 0:
        log.warning("Cópia direta falhou. Re-encode para MP4…")
        log.debug("ffmpeg stderr: %s", result.stderr.decode(errors="replace"))
        saida = os.path.join(pasta_destino, f"{titulo}.mp4")
        cmd_enc = ["ffmpeg", "-y", "-i", video_tmp, "-i", audio_tmp,
                   "-c:v", "libx264", "-crf", "18", "-preset", "medium",
                   "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", saida]
        enc_result = subprocess.run(cmd_enc, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        if enc_result.returncode != 0:
            raise RuntimeError(f"ffmpeg re-encode falhou:\n{enc_result.stderr.decode(errors='replace')}")

    for p in (video_tmp, audio_tmp):
        try:
            os.remove(p)
        except OSError:
            pass

    log.info("Concluído: %s", saida)


def baixar_playlist(url: str, pasta_base: str = "downloads"):
    check_ffmpeg()

    pl = Playlist(url)

    try:
        titulo_pl = pl.title
    except KeyError:
        match = re.search(r"list=([^&]+)", url)
        titulo_pl = match.group(1) if match else "playlist"
        log.warning("Não foi possível obter o título da playlist. Usando '%s' como nome da pasta.", titulo_pl)

    nome_pasta = slugify(titulo_pl)
    pasta_destino = os.path.join(pasta_base, nome_pasta)
    os.makedirs(pasta_destino, exist_ok=True)

    urls = list(pl.video_urls)
    total = len(urls)
    log.info("Playlist: %s (%d vídeos) → %s", titulo_pl, total, pasta_destino)

    for i, video_url in enumerate(urls, 1):
        log.info("[%d/%d] %s", i, total, video_url)
        try:
            baixar_video(video_url, pasta_destino=pasta_destino)
        except Exception as exc:
            log.error("Erro ao baixar %s: %s", video_url, exc)


def is_playlist(url: str) -> bool:
    if not PLAYLIST_PATTERN.search(url):
        return False
    # Playlists de Rádio/Mix (RD, RDMM, RDCLAK...) são geradas pelo algoritmo e não são acessíveis
    list_match = re.search(r"list=([^&]+)", url)
    if list_match and re.match(r"RD", list_match.group(1)):
        return False
    return True


def parse_args():
    parser = argparse.ArgumentParser(
        description="Baixa vídeos/playlists do YouTube na maior resolução, priorizando áudio em PT-BR."
    )
    parser.add_argument("url", nargs="?", help="URL do vídeo ou playlist do YouTube")
    parser.add_argument("-o", "--output", default="downloads", metavar="PASTA",
                        help="Pasta de destino (padrão: downloads)")
    parser.add_argument("-v", "--verbose", action="store_true", help="Exibir logs de debug")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    url = args.url
    while not url:
        try:
            url = input("Cole a URL do vídeo ou playlist do YouTube: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            log.error("Nenhuma URL fornecida. Use: python main.py <URL>")
            raise SystemExit(1)
        if not url:
            log.error("URL não pode ser vazia.")

    if is_playlist(url):
        baixar_playlist(url, pasta_base=args.output)
    else:
        baixar_video(url, pasta_destino=args.output)
