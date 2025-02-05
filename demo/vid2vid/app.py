import gradio as gr

import os
import sys
from typing import Literal, Dict, Optional

import fire
import torch
from torchvision.io import read_video, write_video
from tqdm import tqdm

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from utils.wrapper import StreamDiffusionWrapper

CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))


def main(
    input: str,
    output: str = os.path.join(CURRENT_DIR, "..", "..", "images", "outputs", "output.mp4"),
    model_id: str = "KBlueLeaf/kohaku-v2.1",
    lora_dict: Optional[Dict[str, float]] = None,
    prompt: str = "Surrealistic portrayal of a fantastical dreamscape, inspired by Salvador Dalí's melting landscapes and the vibrant, swirling patterns of psychedelic art. Imagine a scene where gravity is defied, with floating islands and inverted waterfalls. The sky should be a dynamic canvas of neon hues, blending pinks, purples, and electric blues. In the foreground, include bizarre, hybrid creatures that are a mix of organic and geometric forms, reminiscent of Dalí's iconic style. These creatures should be interacting with abstract, clock-like objects, symbolizing the fluidity of time in this dreamscape. The entire composition should have a fluid, dream-like quality, with elements seamlessly transitioning into one another, creating a sense of continuous movement and transformation. The overall mood is one of wonder and exploration, as if the viewer is on a journey through a subconscious realm filled with endless possibilities and surreal beauty. This image should be a visual feast, rich in detail and color, evoking a sense of awe and intrigue.",
    scale: float = 1.0,
    acceleration: Literal["none", "xformers", "tensorrt"] = "xformers",
    use_denoising_batch: bool = True,
    enable_similar_image_filter: bool = True,
    seed: int = 2,
):

    """
    Process for generating images based on a prompt using a specified model.

    Parameters
    ----------
    input : str, optional
        The input video name to load images from.
    output : str, optional
        The output video name to save images to.
    model_id_or_path : str
        The name of the model to use for image generation.
    lora_dict : Optional[Dict[str, float]], optional
        The lora_dict to load, by default None.
        Keys are the LoRA names and values are the LoRA scales.
        Example: {'LoRA_1' : 0.5 , 'LoRA_2' : 0.7 ,...}
    prompt : str
        The prompt to generate images from.
    scale : float, optional
        The scale of the image, by default 1.0.
    acceleration : Literal["none", "xformers", "tensorrt"]
        The type of acceleration to use for image generation.
    use_denoising_batch : bool, optional
        Whether to use denoising batch or not, by default True.
    enable_similar_image_filter : bool, optional
        Whether to enable similar image filter or not,
        by default True.
    seed : int, optional
        The seed, by default 2. if -1, use random seed.
    """

    video_info = read_video(input)
    video = video_info[0] / 255
    fps = video_info[2]["video_fps"]
    height = int(video.shape[1] * scale)
    width = int(video.shape[2] * scale)

    stream = StreamDiffusionWrapper(
        model_id_or_path=model_id,
        lora_dict=lora_dict,
        t_index_list=[35, 45],
        frame_buffer_size=1,
        width=width,
        height=height,
        warmup=10,
        acceleration=acceleration,
        do_add_noise=False,
        mode="img2img",
        output_type="pt",
        enable_similar_image_filter=enable_similar_image_filter,
        similar_image_filter_threshold=0.98,
        use_denoising_batch=use_denoising_batch,
        seed=seed,
    )

    stream.prepare(
        prompt=prompt,
        num_inference_steps=50,
    )

    o = stream(video[0].permute(2, 0, 1))
    height = int(o.shape[1])
    width = int(o.shape[2])
    video_result = torch.zeros(video.shape[0], height, width, 3)

    for _ in range(stream.batch_size):
        stream(image=video[0].permute(2, 0, 1))

    for i in tqdm(range(video.shape[0])):
        output_image = stream(video[i].permute(2, 0, 1))
        video_result[i] = output_image.permute(1, 2, 0)

    video_result = video_result * 255

    write_video(output, video_result[2:], fps=fps)
    return output


demo = gr.Interface(
    main,
    gr.Video(sources=['upload', 'webcam']), 
    "playable_video"
)
demo.launch()
