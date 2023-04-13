# StableDiffusion-on-GKE

**介绍如何在 GKE 上快速运行 [AUTOMATIC1111/stable-diffusion-webui](https://github.com/AUTOMATIC1111/stable-diffusion-webui)，以及如何通过 API 调用 txt2img，img2img, upscaler等任务**

## Build image
使用 Cloud Build 构建镜像，注意最少需要 ```e2-highcpu-8/e2-highcpu-8``` 以上机型，否则build过程会出现OOM报错
```
git clone https://github.com/hxhwing/StableDiffusion-on-GKE.git
gcloud builds submit --region=us-central1 --tag us-central1-docker.pkg.dev/winter-inquiry-377308/stable-diffusion/sd-with-api:minimum --machine-type=e2-highcpu-8
```

## Create GKE cluster and GPU nodes
创建 GKE 集群 和 GPU node pool，运行 Stable Diffusion 建议至少选择 ```n1-standard-8``` 以上机型; 除了 A100 之外，其他所有显卡都只支持 n1 机型；另外请注意开启 ```image streaming```，可大大缩短拉取镜像的时间。
```
gcloud container clusters create "sd-test" \
--zone "us-central1-c" \
--machine-type "n1-standard-8" \
--accelerator "type=nvidia-tesla-t4,count=1" \
--num-nodes "1" \
--enable-autoscaling --min-nodes "1" --max-nodes "3" --location-policy "BALANCED" \
--addons HorizontalPodAutoscaling,HttpLoadBalancing,GcePersistentDiskCsiDriver,GcpFilestoreCsiDriver \
--enable-image-streaming
```


## Deploy resources
### 获取 kubectl context
```
gcloud container clusters get-credentials sd-test --region us-central1-c
```

### 安装 GPU driver
```
kubectl apply -f https://raw.githubusercontent.com/GoogleCloudPlatform/container-engine-accelerators/master/nvidia-driver-installer/cos/daemonset-preloaded.yaml
```

### 部署 Stable Diffusion 资源
> **Note**
>
> 建议将 Automatic1111 的 models 和 outputs 目录放到共享存储 filestore 中，可加快 Pod 扩展时间 (只在第一个Pod第一次启动/运行时下载模型)，以及方便查看和获取输出的图片


#### 部署 filestore
```
kubectl apply -f k8s/filestore-sc.yaml
kubectl apply -f k8s/filestore-pvc.yaml
```

####  部署 Stable Diffusion 资源
```
kubectl apply -f k8s/sd_deployment_filestore.yaml
kubectl apply -f k8s/sd_service.yaml
```

####  部署 HPA
**根据 Cloud Monitoring 中 GPU 利用率(duty cycle) 指标，自动扩展 Stable Diffusion deployment**

部署 GKE external metric adpater，使 GKE 支持从 Cloud Monitoring 中读取 Metric
```
kubectl create clusterrolebinding cluster-admin-binding \
    --clusterrole cluster-admin --user "$(gcloud config get-value account)"

kubectl apply -f https://raw.githubusercontent.com/GoogleCloudPlatform/k8s-stackdriver/master/custom-metrics-stackdriver-adapter/deploy/production/adapter_new_resource_model.yaml
```

部署 HPA (By default: 50% average GPU utilization)
```
kubectl apply -f k8s/sd_hpa.yaml
```

## 访问 Stable Diffusion Web UI
获取 Web UI endpoint:
```
kubectl get service
```

访问 ```http://LoadBalancer-External-IP:7860``` 
> **Note**
>
> 容器启动和运行任务时，会自动下载 SD 1.5 和任务相关的模型，比如upscaler所需的 ESGAN 等模型，保存到 NFS 共享存储的指定目录(/content/stable-diffusion-webui/models/)，其他 Pod 启动时即无需多次下载

![webui](/images/webui.png)


## API 访问 Stable Diffusion

通过 ```http://LoadBalancer-External-IP:7860/docs``` 查看 Automatic1111 WebUI 支持的 API

![API](/images/api.png)

可参考 ```main.py``` 示例代码，通过 [Python API client](https://github.com/mix1009/sdwebuiapi) 访问 AUTOMATIC1111/stable-diffusion-webui

```
from sdwebuiapi.webuiapi import webuiapi

api = webuiapi.WebUIApi(host="104.154.42.128", port=7860, sampler="Euler a", steps=20)

# txt2img
result1 = api.txt2img(prompt="cute cat",
                    negative_prompt="ugly, out of frame",
                    seed=1003,
                    styles=["anime"],
                    cfg_scale=7, 
                    sampler_index='DDIM',                     
                    steps=30,                     
                    enable_hr=True,                      
                    hr_scale=2,                      
                    hr_upscaler=webuiapiHiResUpscaler.Latent,              
                    hr_second_pass_steps=20,                      
                    hr_resize_x=1536,                      
                    hr_resize_y=1024,                      
                    denoising_strength=0.4
                    )
# img2img
result2 = api.img2img(images=[result1.image], prompt="cute tiger", seed=1111, cfg_scale=6.5, denoising_strength=0.6)

# upscaler
result3 = api.extra_single_image(image=result2.image,
                                upscaler_1=webuiapi.Upscaler.ESRGAN_4x,
                                upscaling_resize=2)

```

