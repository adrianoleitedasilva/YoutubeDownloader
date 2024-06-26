from pytube import YouTube
import os
from moviepy.editor import AudioFileClip

def sanitize_filename(filename):
    return "".join(c if c.isalnum() else "_" for c in filename)

def get_available_resolutions(streams):
    resolutions = sorted({stream.resolution for stream in streams.filter(progressive=True)}, key=lambda x: int(x[:-1]))
    return resolutions

def get_available_audio_qualities(streams):
    qualities = sorted({stream.abr for stream in streams.filter(only_audio=True)}, key=lambda x: int(x[:-4]))
    return qualities

def download_video(url, resolution=None, file_type='mp4', output_path=None):
    try:
        print("Downloading video...")
        yt = YouTube(url)

        if file_type == 'mp4':
            streams = yt.streams.filter(progressive=True, file_extension='mp4')
            available_resolutions = get_available_resolutions(streams)
            if resolution and resolution not in available_resolutions:
                raise Exception(f"Resolução {resolution} não disponível. Resoluções disponíveis: {', '.join(available_resolutions)}")
            elif not resolution:
                resolution = available_resolutions[-1]
            video_stream = streams.filter(res=resolution).first()
        elif file_type == 'mp3':
            streams = yt.streams.filter(only_audio=True, file_extension='mp4')
            available_qualities = get_available_audio_qualities(streams)
            if resolution and resolution not in available_qualities:
                raise Exception(f"Qualidade de áudio {resolution} não disponível. Qualidades disponíveis: {', '.join(available_qualities)}")
            elif not resolution:
                resolution = available_qualities[-1]
            video_stream = streams.filter(abr=resolution).first()
        
        if not video_stream:
            raise Exception(f"Nenhum stream disponível para a combinação escolhida de resolução/qualidade {resolution} e tipo {file_type}.")

        if output_path is None:
            sanitized_title = sanitize_filename(yt.title)
            output_path = sanitized_title + ('.mp4' if file_type == 'mp4' else '.mp3')

        download_path = video_stream.download()
        
        if file_type == 'mp3':
            audio_output_path = output_path
            with AudioFileClip(download_path) as audio:
                audio.write_audiofile(audio_output_path)
            os.remove(download_path)

        print(f"Download concluído! Arquivo salvo em: {output_path}")
    except Exception as e:
        print("Ocorreu um erro durante o download:", e)

if __name__ == "__main__":
    video_url = input("Digite a URL do vídeo do YouTube: ")
    yt = YouTube(video_url)

    file_type = input("Digite o tipo de arquivo desejado (mp4 ou mp3): ").lower()

    if file_type == 'mp4':
        streams = yt.streams.filter(progressive=True, file_extension='mp4')
        available_resolutions = get_available_resolutions(streams)
        print(f"Resoluções disponíveis: {', '.join(available_resolutions)}")
        resolution = input("Digite a resolução desejada (ex: 720p) ou deixe em branco para a melhor disponível: ")
    elif file_type == 'mp3':
        streams = yt.streams.filter(only_audio=True, file_extension='mp4')
        available_qualities = get_available_audio_qualities(streams)
        print(f"Qualidades de áudio disponíveis: {', '.join(available_qualities)}")
        resolution = input("Digite a qualidade de áudio desejada (ex: 128kbps) ou deixe em branco para a melhor disponível: ")

    download_video(video_url, resolution, file_type)