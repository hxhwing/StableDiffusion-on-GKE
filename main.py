from PIL import Image
import concurrent
from concurrent.futures import ThreadPoolExecutor
import os
from os import listdir
from time import perf_counter


from sdwebuiapi.webuiapi import webuiapi

api = webuiapi.WebUIApi(host="104.154.42.128", port=7860, sampler="Euler a", steps=20)
folder_dir = "sample_images"


def upscale(image_file):
    if image_file.endswith(".png"):
        print(image_file)
        image_b64 = Image.open(folder_dir + "/" + image_file)
    response = api.extra_single_image(
        image=image_b64,
        upscaler_1=webuiapi.Upscaler.R_ESRGAN_4x,
        upscaling_resize=4,
        upscaler_2=webuiapi.Upscaler.ESRGAN_4x,
        extras_upscaler_2_visibility=0.7,
    )
    dst_file = os.path.basename(image_b64.filename)
    response.image.save("outputs/" + dst_file)
    print("save to outputs/" + dst_file)


t1_start = perf_counter()

# Execute one by one in sequence
# for image in os.listdir(folder_dir):
#     upscale(image)


threads = 5
with ThreadPoolExecutor(max_workers=threads) as executor:
    futures = {executor.submit(upscale, image) for image in os.listdir(folder_dir)}
    for future in concurrent.futures.as_completed(futures):
        try:
            # print()
            data = future.result()
            # print(data)
        except Exception as e:
            print("Something wrong:", e)

t1_stop = perf_counter()
print("Elapsed time during the whole program in seconds:", t1_stop - t1_start)

# # txt2img
# result1 = api.txt2img(prompt="cute squirrel",
#                     negative_prompt="ugly, out of frame",
#                     seed=1003,
#                     styles=["anime"],
#                     cfg_scale=7,
# #                      sampler_index='DDIM',
# #                      steps=30,
# #                      enable_hr=True,
# #                      hr_scale=2,
# #                      hr_upscaler=webuiapi.HiResUpscaler.Latent,
# #                      hr_second_pass_steps=20,
# #                      hr_resize_x=1536,
# #                      hr_resize_y=1024,
# #                      denoising_strength=0.4,

#                     )
# # result1.image

# # print(result1)
# # result1.image.save("result1.jpg")


# # img2img
# result2 = api.img2img(images=[result1.image], prompt="cute tiger", seed=1111, cfg_scale=6.5, denoising_strength=0.6)
# # result2.image

# # Upscaler single
# result3 = api.extra_single_image(image=result2.image,
#                                  upscaler_1=webuiapi.Upscaler.ESRGAN_4x,
#                                  upscaling_resize=2)
# print(result3.image.size)
# # result3.image

# # Upscaler batch
# result4 = api.extra_batch_images(images=[result1.image, result2.image],
#                                  upscaler_1=webuiapi.Upscaler.ESRGAN_4x,
#                                  upscaling_resize=1.5)
# # print(result4)

# # result4.images[0]
# # result4.images[1]
