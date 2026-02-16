# MedForge Validation Logs (Canonical Long Logs)

This file contains consolidated long-form validation outputs and reports.

## Included Artifacts

- gate0-validation-2026-02-16T103320Z.log (superseded run)
- gate0-validation-2026-02-16T103320Z.md (superseded run summary)
- gate0-validation-2026-02-16T103429Z.log (canonical Gate 0 run)
- gate0-validation-2026-02-16T103429Z.md (canonical Gate 0 summary)
- host-validation-2026-02-16.md (Gate 5/6 host validation evidence)

---
## docs/gate0-validation-2026-02-16T103320Z.log

```text
Gate 0 validation run
run_id: 2026-02-16T103320Z
date_utc: 2026-02-16T10:33:20+00:00
log_file: /home/shk/projects/MedForge/docs/gate0-validation-2026-02-16T103320Z.log
report_file: /home/shk/projects/MedForge/docs/gate0-validation-2026-02-16T103320Z.md

## Preflight
hostname: user-System-Product-Name
kernel: Linux 6.8.0-100-generic x86_64 GNU/Linux
docker: Docker version 29.2.1, build a5c7197
domain: medforge.xyz
pack_image: medforge-pack-default@sha256:7e44d4e67aa5c7bbc51701be7f370f45de35794cc7f2504f761b1a510f1c1a6e

## GPU host proof
GPU 0: NVIDIA GeForce RTX 5090 (UUID: GPU-2a3838bd-ff28-e77b-f9e2-47738d6eae8b)
GPU 1: NVIDIA GeForce RTX 5090 (UUID: GPU-9819d8ad-e2ff-83f2-a70b-e9198091b4f0)
GPU 2: NVIDIA GeForce RTX 5090 (UUID: GPU-b766fded-5bf3-a334-68f9-5e421a770bd9)
GPU 3: NVIDIA GeForce RTX 5090 (UUID: GPU-a8bca0c2-09ee-3884-a2a6-bf9bd174c374)
GPU 4: NVIDIA GeForce RTX 5090 (UUID: GPU-6ee9e898-d1a5-6070-a846-ae4171fb5e5a)
GPU 5: NVIDIA GeForce RTX 5090 (UUID: GPU-e87fc627-5ce4-265b-4e1a-96e53001fb63)
GPU 6: NVIDIA GeForce RTX 5090 (UUID: GPU-b668f8be-ce4c-2463-cd26-0001bae260d7)
gpu_count_detected: 7
Mon Feb 16 19:33:21 2026       
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 590.48.01              Driver Version: 590.48.01      CUDA Version: 13.1     |
+-----------------------------------------+------------------------+----------------------+
| GPU  Name                 Persistence-M | Bus-Id          Disp.A | Volatile Uncorr. ECC |
| Fan  Temp   Perf          Pwr:Usage/Cap |           Memory-Usage | GPU-Util  Compute M. |
|                                         |                        |               MIG M. |
|=========================================+========================+======================|
|   0  NVIDIA GeForce RTX 5090        On  |   00000000:01:00.0 Off |                  N/A |
|  0%   26C    P8             14W /  600W |      16MiB /  32607MiB |      0%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+
|   1  NVIDIA GeForce RTX 5090        On  |   00000000:11:00.0 Off |                  N/A |
|  0%   26C    P8              8W /  600W |      16MiB /  32607MiB |      0%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+
|   2  NVIDIA GeForce RTX 5090        On  |   00000000:21:00.0 Off |                  N/A |
|  0%   26C    P8             27W /  600W |      16MiB /  32607MiB |      0%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+
|   3  NVIDIA GeForce RTX 5090        On  |   00000000:C1:00.0 Off |                  N/A |
|  0%   26C    P8              8W /  600W |      16MiB /  32607MiB |      0%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+
|   4  NVIDIA GeForce RTX 5090        On  |   00000000:D1:00.0 Off |                  N/A |
|  0%   26C    P8             28W /  600W |      16MiB /  32607MiB |      0%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+
|   5  NVIDIA GeForce RTX 5090        On  |   00000000:E1:00.0  On |                  N/A |
|  0%   26C    P8             13W /  600W |     189MiB /  32607MiB |      0%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+
|   6  NVIDIA GeForce RTX 5090        On  |   00000000:F1:00.0 Off |                  N/A |
|  0%   26C    P8             15W /  600W |      16MiB /  32607MiB |      0%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+

+-----------------------------------------------------------------------------------------+
| Processes:                                                                              |
|  GPU   GI   CI              PID   Type   Process name                        GPU Memory |
|        ID   ID                                                               Usage      |
|=========================================================================================|
|    0   N/A  N/A            4621      G   /usr/lib/xorg/Xorg                        4MiB |
|    1   N/A  N/A            4621      G   /usr/lib/xorg/Xorg                        4MiB |
|    2   N/A  N/A            4621      G   /usr/lib/xorg/Xorg                        4MiB |
|    3   N/A  N/A            4621      G   /usr/lib/xorg/Xorg                        4MiB |
|    4   N/A  N/A            4621      G   /usr/lib/xorg/Xorg                        4MiB |
|    5   N/A  N/A            4621      G   /usr/lib/xorg/Xorg                      128MiB |
|    5   N/A  N/A            5107      G   /usr/bin/gnome-shell                     32MiB |
|    6   N/A  N/A            4621      G   /usr/lib/xorg/Xorg                        4MiB |
+-----------------------------------------------------------------------------------------+

## GPU in container proof
Mon Feb 16 10:33:21 2026       
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 590.48.01              Driver Version: 590.48.01      CUDA Version: 13.1     |
+-----------------------------------------+------------------------+----------------------+
| GPU  Name                 Persistence-M | Bus-Id          Disp.A | Volatile Uncorr. ECC |
| Fan  Temp   Perf          Pwr:Usage/Cap |           Memory-Usage | GPU-Util  Compute M. |
|                                         |                        |               MIG M. |
|=========================================+========================+======================|
|   0  NVIDIA GeForce RTX 5090        On  |   00000000:01:00.0 Off |                  N/A |
|  0%   26C    P8             14W /  600W |      16MiB /  32607MiB |      0%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+
|   1  NVIDIA GeForce RTX 5090        On  |   00000000:11:00.0 Off |                  N/A |
|  0%   26C    P8              8W /  600W |      16MiB /  32607MiB |      0%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+
|   2  NVIDIA GeForce RTX 5090        On  |   00000000:21:00.0 Off |                  N/A |
|  0%   26C    P8             27W /  600W |      16MiB /  32607MiB |      0%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+
|   3  NVIDIA GeForce RTX 5090        On  |   00000000:C1:00.0 Off |                  N/A |
|  0%   26C    P8              9W /  600W |      16MiB /  32607MiB |      0%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+
|   4  NVIDIA GeForce RTX 5090        On  |   00000000:D1:00.0 Off |                  N/A |
|  0%   26C    P8             28W /  600W |      16MiB /  32607MiB |      0%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+
|   5  NVIDIA GeForce RTX 5090        On  |   00000000:E1:00.0  On |                  N/A |
|  0%   26C    P8             13W /  600W |     189MiB /  32607MiB |      0%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+
|   6  NVIDIA GeForce RTX 5090        On  |   00000000:F1:00.0 Off |                  N/A |
|  0%   26C    P8             15W /  600W |      16MiB /  32607MiB |      0%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+

+-----------------------------------------------------------------------------------------+
| Processes:                                                                              |
|  GPU   GI   CI              PID   Type   Process name                        GPU Memory |
|        ID   ID                                                               Usage      |
|=========================================================================================|
|  No running processes found                                                             |
+-----------------------------------------------------------------------------------------+

## ZFS health proof
NAME   SIZE  ALLOC   FREE  CKPOINT  EXPANDSZ   FRAG    CAP  DEDUP    HEALTH  ALTROOT
tank  39.5G  5.29M  39.5G        -         -     0%     0%  1.00x    ONLINE  -
  pool: tank
 state: ONLINE
config:

	NAME                          STATE     READ WRITE CKSUM
	tank                          ONLINE       0     0     0
	  /var/tmp/medforge-tank.img  ONLINE       0     0     0

errors: No known data errors
tank/medforge/system                                                                                3.40M  38.3G    24K  /tank/medforge/system
tank/medforge/system/db                                                                             3.37M  38.3G  3.37M  /tank/medforge/system/db
tank/medforge/workspaces                                                                            1019K  38.3G    32K  /tank/medforge/workspaces
tank/medforge/workspaces/00000000-0000-0000-0000-0000000000a1                                        373K  38.3G    37K  /tank/medforge/workspaces/00000000-0000-0000-0000-0000000000a1
tank/medforge/workspaces/00000000-0000-0000-0000-0000000000a1/145a60c6-aaf8-4584-af2d-9193fa666e45    24K  38.3G    24K  /tank/medforge/workspaces/00000000-0000-0000-0000-0000000000a1/145a60c6-aaf8-4584-af2d-9193fa666e45
tank/medforge/workspaces/00000000-0000-0000-0000-0000000000a1/184b1f6d-dc65-4c4d-accb-ce91df932e7c    24K  38.3G    24K  /tank/medforge/workspaces/00000000-0000-0000-0000-0000000000a1/184b1f6d-dc65-4c4d-accb-ce91df932e7c
tank/medforge/workspaces/00000000-0000-0000-0000-0000000000a1/377238ad-12ec-4d99-be14-f0045ae6073b    24K  38.3G    24K  /tank/medforge/workspaces/00000000-0000-0000-0000-0000000000a1/377238ad-12ec-4d99-be14-f0045ae6073b
tank/medforge/workspaces/00000000-0000-0000-0000-0000000000a1/4a7f2fc5-757a-4253-8c80-4ec49c8ec24f    24K  38.3G    24K  /tank/medforge/workspaces/00000000-0000-0000-0000-0000000000a1/4a7f2fc5-757a-4253-8c80-4ec49c8ec24f
tank/medforge/workspaces/00000000-0000-0000-0000-0000000000a1/4dce01a6-4558-4c25-a6ee-ef2425614643    24K  38.3G    24K  /tank/medforge/workspaces/00000000-0000-0000-0000-0000000000a1/4dce01a6-4558-4c25-a6ee-ef2425614643
tank/medforge/workspaces/00000000-0000-0000-0000-0000000000a1/5572379d-4dcd-43b9-a15a-7da51c5e2799    24K  38.3G    24K  /tank/medforge/workspaces/00000000-0000-0000-0000-0000000000a1/5572379d-4dcd-43b9-a15a-7da51c5e2799
tank/medforge/workspaces/00000000-0000-0000-0000-0000000000a1/55f79f71-b299-4448-8c28-6aed6f459001    24K  38.3G    24K  /tank/medforge/workspaces/00000000-0000-0000-0000-0000000000a1/55f79f71-b299-4448-8c28-6aed6f459001
tank/medforge/workspaces/00000000-0000-0000-0000-0000000000a1/7e2931de-a704-4e93-afe9-2ce5912c5271    24K  38.3G    24K  /tank/medforge/workspaces/00000000-0000-0000-0000-0000000000a1/7e2931de-a704-4e93-afe9-2ce5912c5271
tank/medforge/workspaces/00000000-0000-0000-0000-0000000000a1/94e97085-0e50-4cae-9d05-b160b2b714a5    24K  38.3G    24K  /tank/medforge/workspaces/00000000-0000-0000-0000-0000000000a1/94e97085-0e50-4cae-9d05-b160b2b714a5
tank/medforge/workspaces/00000000-0000-0000-0000-0000000000a1/9a7d9ae2-022b-49ae-a7e1-2965eb8cb90e    24K  38.3G    24K  /tank/medforge/workspaces/00000000-0000-0000-0000-0000000000a1/9a7d9ae2-022b-49ae-a7e1-2965eb8cb90e
tank/medforge/workspaces/00000000-0000-0000-0000-0000000000a1/9ff09f49-e07c-4348-94b1-ed4e75aaeab1    24K  38.3G    24K  /tank/medforge/workspaces/00000000-0000-0000-0000-0000000000a1/9ff09f49-e07c-4348-94b1-ed4e75aaeab1
tank/medforge/workspaces/00000000-0000-0000-0000-0000000000a1/bbfbdf6b-84a2-4810-97c5-80a1ff79f26d    24K  38.3G    24K  /tank/medforge/workspaces/00000000-0000-0000-0000-0000000000a1/bbfbdf6b-84a2-4810-97c5-80a1ff79f26d
tank/medforge/workspaces/00000000-0000-0000-0000-0000000000a1/e4f40841-d126-41f2-a1d8-fc86263490af    24K  38.3G    24K  /tank/medforge/workspaces/00000000-0000-0000-0000-0000000000a1/e4f40841-d126-41f2-a1d8-fc86263490af
tank/medforge/workspaces/00000000-0000-0000-0000-0000000000a1/edd5696d-9911-4cd9-a209-b1b6026062b9    24K  38.3G    24K  /tank/medforge/workspaces/00000000-0000-0000-0000-0000000000a1/edd5696d-9911-4cd9-a209-b1b6026062b9
tank/medforge/workspaces/00000000-0000-0000-0000-0000000000b2                                        326K  38.3G    38K  /tank/medforge/workspaces/00000000-0000-0000-0000-0000000000b2
tank/medforge/workspaces/00000000-0000-0000-0000-0000000000b2/1de35429-5f32-4cf7-ac87-0cc16e9383b8    24K  38.3G    24K  /tank/medforge/workspaces/00000000-0000-0000-0000-0000000000b2/1de35429-5f32-4cf7-ac87-0cc16e9383b8
tank/medforge/workspaces/00000000-0000-0000-0000-0000000000b2/2a798045-b9d1-41e9-b222-44b6ccf09e59    24K  38.3G    24K  /tank/medforge/workspaces/00000000-0000-0000-0000-0000000000b2/2a798045-b9d1-41e9-b222-44b6ccf09e59
tank/medforge/workspaces/00000000-0000-0000-0000-0000000000b2/76b00948-9ae0-4ee3-a22d-f864fa593d71    24K  38.3G    24K  /tank/medforge/workspaces/00000000-0000-0000-0000-0000000000b2/76b00948-9ae0-4ee3-a22d-f864fa593d71
tank/medforge/workspaces/00000000-0000-0000-0000-0000000000b2/840a5066-39ee-4a1b-ab15-064ce7b66040    24K  38.3G    24K  /tank/medforge/workspaces/00000000-0000-0000-0000-0000000000b2/840a5066-39ee-4a1b-ab15-064ce7b66040
tank/medforge/workspaces/00000000-0000-0000-0000-0000000000b2/9ea62c95-b555-434c-aedd-2dfbdfce1abf    24K  38.3G    24K  /tank/medforge/workspaces/00000000-0000-0000-0000-0000000000b2/9ea62c95-b555-434c-aedd-2dfbdfce1abf
tank/medforge/workspaces/00000000-0000-0000-0000-0000000000b2/a44374c5-01ce-4ee4-8d3b-26004c42729a    24K  38.3G    24K  /tank/medforge/workspaces/00000000-0000-0000-0000-0000000000b2/a44374c5-01ce-4ee4-8d3b-26004c42729a
tank/medforge/workspaces/00000000-0000-0000-0000-0000000000b2/a4b3e5d6-5c79-4a48-8545-ace2d4499fcd    24K  38.3G    24K  /tank/medforge/workspaces/00000000-0000-0000-0000-0000000000b2/a4b3e5d6-5c79-4a48-8545-ace2d4499fcd
tank/medforge/workspaces/00000000-0000-0000-0000-0000000000b2/a5d665de-3a50-4439-80c1-55c385795b5a    24K  38.3G    24K  /tank/medforge/workspaces/00000000-0000-0000-0000-0000000000b2/a5d665de-3a50-4439-80c1-55c385795b5a
tank/medforge/workspaces/00000000-0000-0000-0000-0000000000b2/adcd182a-a413-492f-b201-759652e70612    24K  38.3G    24K  /tank/medforge/workspaces/00000000-0000-0000-0000-0000000000b2/adcd182a-a413-492f-b201-759652e70612
tank/medforge/workspaces/00000000-0000-0000-0000-0000000000b2/bf8ec019-95ad-40fa-94ef-c79b52ccd45d    24K  38.3G    24K  /tank/medforge/workspaces/00000000-0000-0000-0000-0000000000b2/bf8ec019-95ad-40fa-94ef-c79b52ccd45d
tank/medforge/workspaces/00000000-0000-0000-0000-0000000000b2/d2c7a2e1-e6d3-4c14-b4fe-2fd9dd12c5a1    24K  38.3G    24K  /tank/medforge/workspaces/00000000-0000-0000-0000-0000000000b2/d2c7a2e1-e6d3-4c14-b4fe-2fd9dd12c5a1
tank/medforge/workspaces/00000000-0000-0000-0000-0000000000b2/e629ea75-4755-49f8-916a-f0ea6394d3c7    24K  38.3G    24K  /tank/medforge/workspaces/00000000-0000-0000-0000-0000000000b2/e629ea75-4755-49f8-916a-f0ea6394d3c7
tank/medforge/workspaces/0703ed44-14a4-424f-9f07-092512fc5498                                         48K  38.3G    24K  /tank/medforge/workspaces/0703ed44-14a4-424f-9f07-092512fc5498
tank/medforge/workspaces/0703ed44-14a4-424f-9f07-092512fc5498/c916ff08-7cf4-45c3-bed1-67a282977590    24K  38.3G    24K  /tank/medforge/workspaces/0703ed44-14a4-424f-9f07-092512fc5498/c916ff08-7cf4-45c3-bed1-67a282977590
tank/medforge/workspaces/1215c65c-d646-4585-8ee4-4ef3064f2d28                                         48K  38.3G    24K  /tank/medforge/workspaces/1215c65c-d646-4585-8ee4-4ef3064f2d28
tank/medforge/workspaces/1215c65c-d646-4585-8ee4-4ef3064f2d28/62297226-acdd-4258-bbd6-799d52103485    24K  38.3G    24K  /tank/medforge/workspaces/1215c65c-d646-4585-8ee4-4ef3064f2d28/62297226-acdd-4258-bbd6-799d52103485
tank/medforge/workspaces/4c6a88c2-8670-4dfe-ab3d-4d638496bf7d                                         48K  38.3G    24K  /tank/medforge/workspaces/4c6a88c2-8670-4dfe-ab3d-4d638496bf7d
tank/medforge/workspaces/4c6a88c2-8670-4dfe-ab3d-4d638496bf7d/9d78243b-538c-4c09-b03f-b86adb7bd0f4    24K  38.3G    24K  /tank/medforge/workspaces/4c6a88c2-8670-4dfe-ab3d-4d638496bf7d/9d78243b-538c-4c09-b03f-b86adb7bd0f4
tank/medforge/workspaces/762b9771-9b90-4964-8967-12c9a22d4a2d                                         48K  38.3G    24K  /tank/medforge/workspaces/762b9771-9b90-4964-8967-12c9a22d4a2d
tank/medforge/workspaces/762b9771-9b90-4964-8967-12c9a22d4a2d/c62f05bf-83b8-4a97-b8e2-33b5c27ebdab    24K  38.3G    24K  /tank/medforge/workspaces/762b9771-9b90-4964-8967-12c9a22d4a2d/c62f05bf-83b8-4a97-b8e2-33b5c27ebdab
tank/medforge/workspaces/970723e2-17d0-4958-bebb-8826a2361b98                                         48K  38.3G    24K  /tank/medforge/workspaces/970723e2-17d0-4958-bebb-8826a2361b98
tank/medforge/workspaces/970723e2-17d0-4958-bebb-8826a2361b98/17f73276-7d8a-41dd-864a-b4d6f81eb5cb    24K  38.3G    24K  /tank/medforge/workspaces/970723e2-17d0-4958-bebb-8826a2361b98/17f73276-7d8a-41dd-864a-b4d6f81eb5cb
tank/medforge/workspaces/d5cb722e-dc03-477b-bc6f-b63ddc94f947                                         48K  38.3G    24K  /tank/medforge/workspaces/d5cb722e-dc03-477b-bc6f-b63ddc94f947
tank/medforge/workspaces/d5cb722e-dc03-477b-bc6f-b63ddc94f947/a00ee4fb-3b54-4162-a35a-a31851590e84    24K  38.3G    24K  /tank/medforge/workspaces/d5cb722e-dc03-477b-bc6f-b63ddc94f947/a00ee4fb-3b54-4162-a35a-a31851590e84

## ZFS write/read + snapshot proof
probe_readback: gate0-2026-02-16T103320Z
NAME                                                                            USED  AVAIL  REFER  MOUNTPOINT
tank/medforge/workspaces/gate0-validation-20260216103320@gate0-20260216103320     0B      -    24K  -

## DNS wildcard proof
getent medforge.medforge.xyz
61.72.69.176    medforge.medforge.xyz
getent api.medforge.medforge.xyz
61.72.69.176    medforge.medforge.xyz api.medforge.medforge.xyz
getent s-gate0check.medforge.medforge.xyz
61.72.69.176    medforge.medforge.xyz s-gate0check.medforge.medforge.xyz
resolved_base_ip: 61.72.69.176
resolved_api_ip: 61.72.69.176
resolved_wild_ip: 61.72.69.176

## TLS strict proof
curl_status_base: 200
curl_status_api_healthz: 200
curl_status_wild_session_proxy: 401
depth=2 C = US, O = Internet Security Research Group, CN = ISRG Root X1
verify return:1
depth=1 C = US, O = Let's Encrypt, CN = E8
verify return:1
depth=0 CN = medforge.medforge.xyz
verify return:1
CONNECTED(00000003)
---
Certificate chain
 0 s:CN = medforge.medforge.xyz
   i:C = US, O = Let's Encrypt, CN = E8
   a:PKEY: id-ecPublicKey, 256 (bit); sigalg: ecdsa-with-SHA384
   v:NotBefore: Feb 16 08:31:10 2026 GMT; NotAfter: May 17 08:31:09 2026 GMT
 1 s:C = US, O = Let's Encrypt, CN = E8
   i:C = US, O = Internet Security Research Group, CN = ISRG Root X1
   a:PKEY: id-ecPublicKey, 384 (bit); sigalg: RSA-SHA256
   v:NotBefore: Mar 13 00:00:00 2024 GMT; NotAfter: Mar 12 23:59:59 2027 GMT
---
Server certificate
-----BEGIN CERTIFICATE-----
MIIDkzCCAxmgAwIBAgISBr/9+UZctg8hlj+PTJSSgM0mMAoGCCqGSM49BAMDMDIx
CzAJBgNVBAYTAlVTMRYwFAYDVQQKEw1MZXQncyBFbmNyeXB0MQswCQYDVQQDEwJF
ODAeFw0yNjAyMTYwODMxMTBaFw0yNjA1MTcwODMxMDlaMCAxHjAcBgNVBAMTFW1l
ZGZvcmdlLm1lZGZvcmdlLnh5ejBZMBMGByqGSM49AgEGCCqGSM49AwEHA0IABDs2
Aa3k9MQm/TDiZU0YCITKVkHa6CV+OYpnWJnBpbp71wwOKhJMLUWb04dEbWBDzhjt
/gKwaLUuKvSuYG+9FJ2jggIfMIICGzAOBgNVHQ8BAf8EBAMCB4AwEwYDVR0lBAww
CgYIKwYBBQUHAwEwDAYDVR0TAQH/BAIwADAdBgNVHQ4EFgQU2S9s9Ddd9tPPaRe8
cYWYt5whbHgwHwYDVR0jBBgwFoAUjw0TovYuftFQbDMYOF1ZjiNykcowMgYIKwYB
BQUHAQEEJjAkMCIGCCsGAQUFBzAChhZodHRwOi8vZTguaS5sZW5jci5vcmcvMCAG
A1UdEQQZMBeCFW1lZGZvcmdlLm1lZGZvcmdlLnh5ejATBgNVHSAEDDAKMAgGBmeB
DAECATAtBgNVHR8EJjAkMCKgIKAehhxodHRwOi8vZTguYy5sZW5jci5vcmcvMzku
Y3JsMIIBCgYKKwYBBAHWeQIEAgSB+wSB+AD2AHUAZBHEbKQS7KeJHKICLgC8q08o
B9QeNSer6v7VA8l9zfAAAAGcZci+RAAABAMARjBEAiAy5ldJdKvkvtTwzOeaMngx
6gceaz+XA0S+D81OobH6wgIgOWrEjQdF9Yz44dc1GahSNmxoAAruSindw5zD154V
COIAfQAai51pSleYyJmgyoi99I/AtFZgzMNgDR9x9Gn/x9GsowAAAZxlyMUFAAgA
AAUASNx4UwQDAEYwRAIgbyvo0vO52i/3pnXrbDoW9SPbSMfSCrl/WYaA2sOSnlcC
IEMpO4yoFkZgRz/OnUE61HQoQ5MfsaQAIEEH/cyeB8LUMAoGCCqGSM49BAMDA2gA
MGUCMCl9I18hTMwhe4eCBqKbhuyK9784aRgVM0XlGdSOvr+HmPkokK1hk1whoHQo
koTkVAIxAMnlAlLlVvXE6gSL486aYpO3cjO4/8fvWX6AGs+YIzaeMlQZGjuijLjW
0aeYVgcrdg==
-----END CERTIFICATE-----
subject=CN = medforge.medforge.xyz
issuer=C = US, O = Let's Encrypt, CN = E8
---
No client certificate CA names sent
Peer signing digest: SHA256
Peer signature type: ECDSA
Server Temp Key: X25519, 253 bits
---
SSL handshake has read 2397 bytes and written 387 bytes
Verification: OK
Verified peername: medforge.medforge.xyz
---
New, TLSv1.3, Cipher is TLS_AES_128_GCM_SHA256
Server public key is 256 bit
Secure Renegotiation IS NOT supported
Compression: NONE
Expansion: NONE
No ALPN negotiated
Early data was not sent
Verify return code: 0 (ok)
---
DONE
---
Post-Handshake New Session Ticket arrived:
SSL-Session:
    Protocol  : TLSv1.3
    Cipher    : TLS_AES_128_GCM_SHA256
    Session-ID: AF0803EA88CA4B2A3D095C99BA03A94F978AA702C6804E4941833A1216F1ABBD
    Session-ID-ctx: 
    Resumption PSK: 09CDB0859976685A2F285519FE1E03EFA78D0E01146C2B88DD896A23CB1551EF
    PSK identity: None
    PSK identity hint: None
    SRP username: None
    TLS session ticket lifetime hint: 604800 (seconds)
    TLS session ticket:
    0000 - e8 38 56 8c 56 b0 41 86-d0 61 34 22 19 d3 d3 04   .8V.V.A..a4"....
    0010 - 2f f4 e6 39 33 b5 09 ee-06 3e da c2 fd e7 1c fd   /..93....>......
    0020 - 99 c8 46 df 80 18 25 ee-02 54 61 cc 9d 37 1e b8   ..F...%..Ta..7..
    0030 - 54 2f c6 88 6a d9 09 e4-c4 c4 39 d0 8f d1 56 e9   T/..j.....9...V.
    0040 - 5a 8f 47 f7 ed 99 0c 43-65 d9 7c cf a0 05 e7 5d   Z.G....Ce.|....]
    0050 - 27 d3 c4 0b 5b a9 78 6c-e8 60 5b 06 b0 73 74 50   '...[.xl.`[..stP
    0060 - 40 34 08 22 3d ae 83 66-7e                        @4."=..f~

    Start Time: 1771238002
    Timeout   : 7200 (sec)
    Verify return code: 0 (ok)
    Extended master secret: no
    Max Early Data: 0
---
read R BLOCK
depth=2 C = US, O = Internet Security Research Group, CN = ISRG Root X1
verify return:1
depth=1 C = US, O = Let's Encrypt, CN = E7
verify return:1
depth=0 CN = *.medforge.medforge.xyz
verify return:1
CONNECTED(00000003)
---
Certificate chain
 0 s:CN = *.medforge.medforge.xyz
   i:C = US, O = Let's Encrypt, CN = E7
   a:PKEY: id-ecPublicKey, 256 (bit); sigalg: ecdsa-with-SHA384
   v:NotBefore: Feb 16 08:31:10 2026 GMT; NotAfter: May 17 08:31:09 2026 GMT
 1 s:C = US, O = Let's Encrypt, CN = E7
   i:C = US, O = Internet Security Research Group, CN = ISRG Root X1
   a:PKEY: id-ecPublicKey, 384 (bit); sigalg: RSA-SHA256
   v:NotBefore: Mar 13 00:00:00 2024 GMT; NotAfter: Mar 12 23:59:59 2027 GMT
---
Server certificate
-----BEGIN CERTIFICATE-----
MIIDkTCCAxagAwIBAgISBgf2mce/9La4NKZgIBmoqWCFMAoGCCqGSM49BAMDMDIx
CzAJBgNVBAYTAlVTMRYwFAYDVQQKEw1MZXQncyBFbmNyeXB0MQswCQYDVQQDEwJF
NzAeFw0yNjAyMTYwODMxMTBaFw0yNjA1MTcwODMxMDlaMCIxIDAeBgNVBAMMFyou
bWVkZm9yZ2UubWVkZm9yZ2UueHl6MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE
l9AgdIzdk7ACZHbiaqjx5I9z6hnHfBNXNCtTp2LFoHdsbub0vGP5HU/DJODuentk
jCW07SXBc2DTggUuCSOEV6OCAhowggIWMA4GA1UdDwEB/wQEAwIHgDATBgNVHSUE
DDAKBggrBgEFBQcDATAMBgNVHRMBAf8EAjAAMB0GA1UdDgQWBBS8atUXUI7BYofk
6cBVk2ADIXyAOTAfBgNVHSMEGDAWgBSuSJ7chx1EoG/aouVgdAR4wpwAgDAyBggr
BgEFBQcBAQQmMCQwIgYIKwYBBQUHMAKGFmh0dHA6Ly9lNy5pLmxlbmNyLm9yZy8w
IgYDVR0RBBswGYIXKi5tZWRmb3JnZS5tZWRmb3JnZS54eXowEwYDVR0gBAwwCjAI
BgZngQwBAgEwLAYDVR0fBCUwIzAhoB+gHYYbaHR0cDovL2U3LmMubGVuY3Iub3Jn
LzYuY3JsMIIBBAYKKwYBBAHWeQIEAgSB9QSB8gDwAHYAFoMtq/CpJQ8P8DqlRf/I
v8gj0IdL9gQpJ/jnHzMT9foAAAGcZci+vAAABAMARzBFAiAQPbTAcG9xFhc/BSdH
SF4pxu7atDCphkILZUGAnNktNgIhAMH6211MVpwH5E51M3XIwRMtS+ndt7/ePAgk
cdMDcs5oAHYADleUvPOuqT4zGyyZB7P3kN+bwj1xMiXdIaklrGHFTiEAAAGcZci+
wgAABAMARzBFAiEA9oH2c1RPiQeQThfprmGu1/Yx9P3reNDzofKpDSs5DmUCIFa6
iv/bKS8Phplt/pM00qBReEwc+Xfy3G48P3uKf450MAoGCCqGSM49BAMDA2kAMGYC
MQCIjIzhBfXCZtzPxZH9GyW/dAEcE3sCU3YO1KbefsSLHrHi4DVfMVA9/cmEeNTw
QFACMQD4eRpx8/7wSgo1BFgRqyeff2eLMA4h799gZdls0sW/R/tKU2vth4bTbK2K
PuTRve4=
-----END CERTIFICATE-----
subject=CN = *.medforge.medforge.xyz
issuer=C = US, O = Let's Encrypt, CN = E7
---
No client certificate CA names sent
Peer signing digest: SHA256
Peer signature type: ECDSA
Server Temp Key: X25519, 253 bits
---
SSL handshake has read 2395 bytes and written 400 bytes
Verification: OK
Verified peername: *.medforge.medforge.xyz
---
New, TLSv1.3, Cipher is TLS_AES_128_GCM_SHA256
Server public key is 256 bit
Secure Renegotiation IS NOT supported
Compression: NONE
Expansion: NONE
No ALPN negotiated
Early data was not sent
Verify return code: 0 (ok)
---
DONE
---
Post-Handshake New Session Ticket arrived:
SSL-Session:
    Protocol  : TLSv1.3
    Cipher    : TLS_AES_128_GCM_SHA256
    Session-ID: 576C2021DEABE081D37387D31D8E5423241124E1463A8FDC5072BD2BCCD8D75A
    Session-ID-ctx: 
    Resumption PSK: 096533892E379519F18696B366831A319125932164FD794581BDB63DC7A71B2B
    PSK identity: None
    PSK identity hint: None
    SRP username: None
    TLS session ticket lifetime hint: 604800 (seconds)
    TLS session ticket:
    0000 - db 3b af 4c 89 34 f4 e9-5b 97 9c 9d 22 14 73 fb   .;.L.4..[...".s.
    0010 - 63 0b 5d fd 7e 3c eb 4b-e9 08 b9 2e cc 71 cd df   c.].~<.K.....q..
    0020 - e2 f6 a7 c1 a2 45 ad de-21 a0 28 65 68 af 80 18   .....E..!.(eh...
    0030 - 9e 8b 12 ae 14 53 49 1c-51 60 48 be 9d 08 40 66   .....SI.Q`H...@f
    0040 - 75 91 37 d0 40 04 78 d5-d8 b7 e6 0a 2b 6f c8 8d   u.7.@.x.....+o..
    0050 - d1 a9 fa 99 23 d9 c2 a0-b8 7d 11 2f 48 47 15 4b   ....#....}./HG.K
    0060 - 62 d8 47 0a 73 7c 2e 8f-1d                        b.G.s|...

    Start Time: 1771238002
    Timeout   : 7200 (sec)
    Verify return code: 0 (ok)
    Extended master secret: no
    Max Early Data: 0
---
read R BLOCK
subject=CN = medforge.medforge.xyz
issuer=C = US, O = Let's Encrypt, CN = E8
notBefore=Feb 16 08:31:10 2026 GMT
notAfter=May 17 08:31:09 2026 GMT
X509v3 Subject Alternative Name: 
    DNS:medforge.medforge.xyz
ERROR: wildcard SAN missing for *.medforge.medforge.xyz

## Gate 0 verdict
GPU host: PASS
GPU container: PASS
ZFS health: PASS
ZFS write/read: PASS
ZFS snapshot: PASS
DNS wildcard: PASS
TLS strict: FAIL
OVERALL: FAIL
/bin/bash: line 228: medforge.xyz\: command not found
/bin/bash: line 228: medforge-pack-default@sha256:7e44d4e67aa5c7bbc51701be7f370f45de35794cc7f2504f761b1a510f1c1a6e\: command not found
/bin/bash: line 228: docs/gate0-validation-2026-02-16T103320Z.log\: No such file or directory
/bin/bash: line 228: nvidia-smi\: command not found
/bin/bash: line 226: pack_image: No such file or directory
unrecognized command 'list/status\'
usage: zpool command args ...
where 'command' is one of the following:

	version

	create [-fnd] [-o property=value] ... 
	    [-O file-system-property=value] ... 
	    [-m mountpoint] [-R root] <pool> <vdev> ...
	destroy [-f] <pool>

	add [-fgLnP] [-o property=value] <pool> <vdev> ...
	remove [-npsw] <pool> <device> ...

	labelclear [-f] <vdev>

	checkpoint [-d [-w]] <pool> ...

	list [-gHLpPv] [-o property[,...]] [-T d|u] [pool] ... 
	    [interval [count]]
	iostat [[[-c [script1,script2,...][-lq]]|[-rw]] [-T d | u] [-ghHLpPvy]
	    [[pool ...]|[pool vdev ...]|[vdev ...]] [[-n] interval [count]]
	status [-c [script1,script2,...]] [-igLpPstvxD]  [-T d|u] [pool] ... 
	    [interval [count]]

	online [-e] <pool> <device> ...
	offline [-f] [-t] <pool> <device> ...
	clear [-nF] <pool> [device]
	reopen [-n] <pool>

	attach [-fsw] [-o property=value] <pool> <device> <new-device>
	detach <pool> <device>
	replace [-fsw] [-o property=value] <pool> <device> [new-device]
	split [-gLnPl] [-R altroot] [-o mntopts]
	    [-o property=value] <pool> <newpool> [<device> ...]

	initialize [-c | -s | -u] [-w] <pool> [<device> ...]
	resilver <pool> ...
	scrub [-s | -p] [-w] [-e] <pool> ...
	trim [-dw] [-r <rate>] [-c | -s] <pool> [<device> ...]

	import [-d dir] [-D]
	import [-o mntopts] [-o property=value] ... 
	    [-d dir | -c cachefile] [-D] [-l] [-f] [-m] [-N] [-R root] [-F [-n]] -a
	import [-o mntopts] [-o property=value] ... 
	    [-d dir | -c cachefile] [-D] [-l] [-f] [-m] [-N] [-R root] [-F [-n]]
	    [--rewind-to-checkpoint] <pool | id> [newpool]
	export [-af] <pool> ...
	upgrade
	upgrade -v
	upgrade [-V version] <-a | pool ...>
	reguid <pool>

	history [-il] [<pool>] ...
	events [-vHf [pool] | -c]

	get [-Hp] [-o "all" | field[,...]] <"all" | property[,...]> <pool> ...
	set <property=value> <pool>
	set <vdev_property=value> <pool> <vdev>
	sync [pool] ...

	wait [-Hp] [-T d|u] [-t <activity>[,...]] <pool> [interval]

For further help on a command or topic, run: zpool help [<topic>]
/bin/bash: line 228: tank/medforge/workspaces/gate0-validation-20260216103320\: No such file or directory
/bin/bash: line 228: tank/medforge/workspaces/gate0-validation-20260216103320@gate0-20260216103320\: No such file or directory
/bin/bash: line 228: medforge.medforge.xyz\: command not found
/bin/bash: line 228: api.medforge.medforge.xyz\: command not found
/bin/bash: line 228: s-gate0check.medforge.medforge.xyz\: command not found
/bin/bash: line 228: 61.72.69.176\: command not found
/bin/bash: line 228: *.medforge.medforge.xyz\: command not found
/bin/bash: line 228: nvidia-smi\: command not found
/bin/bash: line 226: pack_image: No such file or directory
unrecognized command 'list\'
usage: zpool command args ...
where 'command' is one of the following:

	version

	create [-fnd] [-o property=value] ... 
	    [-O file-system-property=value] ... 
	    [-m mountpoint] [-R root] <pool> <vdev> ...
	destroy [-f] <pool>

	add [-fgLnP] [-o property=value] <pool> <vdev> ...
	remove [-npsw] <pool> <device> ...

	labelclear [-f] <vdev>

	checkpoint [-d [-w]] <pool> ...

	list [-gHLpPv] [-o property[,...]] [-T d|u] [pool] ... 
	    [interval [count]]
	iostat [[[-c [script1,script2,...][-lq]]|[-rw]] [-T d | u] [-ghHLpPvy]
	    [[pool ...]|[pool vdev ...]|[vdev ...]] [[-n] interval [count]]
	status [-c [script1,script2,...]] [-igLpPstvxD]  [-T d|u] [pool] ... 
	    [interval [count]]

	online [-e] <pool> <device> ...
	offline [-f] [-t] <pool> <device> ...
	clear [-nF] <pool> [device]
	reopen [-n] <pool>

	attach [-fsw] [-o property=value] <pool> <device> <new-device>
	detach <pool> <device>
	replace [-fsw] [-o property=value] <pool> <device> [new-device]
	split [-gLnPl] [-R altroot] [-o mntopts]
	    [-o property=value] <pool> <newpool> [<device> ...]

	initialize [-c | -s | -u] [-w] <pool> [<device> ...]
	resilver <pool> ...
	scrub [-s | -p] [-w] [-e] <pool> ...
	trim [-dw] [-r <rate>] [-c | -s] <pool> [<device> ...]

	import [-d dir] [-D]
	import [-o mntopts] [-o property=value] ... 
	    [-d dir | -c cachefile] [-D] [-l] [-f] [-m] [-N] [-R root] [-F [-n]] -a
	import [-o mntopts] [-o property=value] ... 
	    [-d dir | -c cachefile] [-D] [-l] [-f] [-m] [-N] [-R root] [-F [-n]]
	    [--rewind-to-checkpoint] <pool | id> [newpool]
	export [-af] <pool> ...
	upgrade
	upgrade -v
	upgrade [-V version] <-a | pool ...>
	reguid <pool>

	history [-il] [<pool>] ...
	events [-vHf [pool] | -c]

	get [-Hp] [-o "all" | field[,...]] <"all" | property[,...]> <pool> ...
	set <property=value> <pool>
	set <vdev_property=value> <pool> <vdev>
	sync [pool] ...

	wait [-Hp] [-T d|u] [-t <activity>[,...]] <pool> [interval]

For further help on a command or topic, run: zpool help [<topic>]
cannot open 'tank\': invalid character '\' in pool name
unrecognized command 'list\'
usage: zfs command args ...
where 'command' is one of the following:

	version

	create [-Pnpuv] [-o property=value] ... <filesystem>
	create [-Pnpsv] [-b blocksize] [-o property=value] ... -V <size> <volume>
	destroy [-fnpRrv] <filesystem|volume>
	destroy [-dnpRrv] <filesystem|volume>@<snap>[%<snap>][,...]
	destroy <filesystem|volume>#<bookmark>

	snapshot [-r] [-o property=value] ... <filesystem|volume>@<snap> ...
	rollback [-rRf] <snapshot>
	clone [-p] [-o property=value] ... <snapshot> <filesystem|volume>
	promote <clone-filesystem>
	rename [-f] <filesystem|volume|snapshot> <filesystem|volume|snapshot>
	rename -p [-f] <filesystem|volume> <filesystem|volume>
	rename -u [-f] <filesystem> <filesystem>
	rename -r <snapshot> <snapshot>
	bookmark <snapshot|bookmark> <newbookmark>
	program [-jn] [-t <instruction limit>] [-m <memory limit (b)>]
	    <pool> <program file> [lua args...]

	list [-Hp] [-r|-d max] [-o property[,...]] [-s property]...
	    [-S property]... [-t type[,...]] [filesystem|volume|snapshot] ...

	set [-u] <property=value> ... <filesystem|volume|snapshot> ...
	get [-rHp] [-d max] [-o "all" | field[,...]]
	    [-t type[,...]] [-s source[,...]]
	    <"all" | property[,...]> [filesystem|volume|snapshot|bookmark] ...
	inherit [-rS] <property> <filesystem|volume|snapshot> ...
	upgrade [-v]
	upgrade [-r] [-V version] <-a | filesystem ...>

	userspace [-Hinp] [-o field[,...]] [-s field] ...
	    [-S field] ... [-t type[,...]] <filesystem|snapshot|path>
	groupspace [-Hinp] [-o field[,...]] [-s field] ...
	    [-S field] ... [-t type[,...]] <filesystem|snapshot|path>
	projectspace [-Hp] [-o field[,...]] [-s field] ... 
	    [-S field] ... <filesystem|snapshot|path>

	project [-d|-r] <directory|file ...>
	project -c [-0] [-d|-r] [-p id] <directory|file ...>
	project -C [-k] [-r] <directory ...>
	project [-p id] [-r] [-s] <directory ...>

	mount
	mount [-flvO] [-o opts] <-a | filesystem>
	unmount [-fu] <-a | filesystem|mountpoint>
	share [-l] <-a [nfs|smb] | filesystem>
	unshare <-a [nfs|smb] | filesystem|mountpoint>

	send [-DLPbcehnpsVvw] [-i|-I snapshot]
	     [-R [-X dataset[,dataset]...]]     <snapshot>
	send [-DnVvPLecw] [-i snapshot|bookmark] <filesystem|volume|snapshot>
	send [-DnPpVvLec] [-i bookmark|snapshot] --redact <bookmark> <snapshot>
	send [-nVvPe] -t <receive_resume_token>
	send [-PnVv] --saved filesystem
	receive [-vMnsFhu] [-o <property>=<value>] ... [-x <property>] ...
	    <filesystem|volume|snapshot>
	receive [-vMnsFhu] [-o <property>=<value>] ... [-x <property>] ... 
	    [-d | -e] <filesystem>
	receive -A <filesystem|volume>

	allow <filesystem|volume>
	allow [-ldug] <"everyone"|user|group>[,...] <perm|@setname>[,...]
	    <filesystem|volume>
	allow [-ld] -e <perm|@setname>[,...] <filesystem|volume>
	allow -c <perm|@setname>[,...] <filesystem|volume>
	allow -s @setname <perm|@setname>[,...] <filesystem|volume>

	unallow [-rldug] <"everyone"|user|group>[,...]
	    [<perm|@setname>[,...]] <filesystem|volume>
	unallow [-rld] -e [<perm|@setname>[,...]] <filesystem|volume>
	unallow [-r] -c [<perm|@setname>[,...]] <filesystem|volume>
	unallow [-r] -s @setname [<perm|@setname>[,...]] <filesystem|volume>

	hold [-r] <tag> <snapshot> ...
	holds [-rHp] <snapshot> ...
	release [-r] <tag> <snapshot> ...
	diff [-FHth] <snapshot> [snapshot|filesystem]
	load-key [-rn] [-L <keylocation>] <-a | filesystem|volume>
	unload-key [-r] <-a | filesystem|volume>
	change-key [-l] [-o keyformat=<value>]
	    [-o keylocation=<value>] [-o pbkdf2iters=<value>]
	    <filesystem|volume>
	change-key -i [-l] <filesystem|volume>
	redact <snapshot> <bookmark> <redaction_snapshot> ...
	wait [-t <activity>] <filesystem>
	zone <nsfile> <filesystem>
	unzone <nsfile> <filesystem>

Each dataset is of the form: pool/[dataset/]*dataset[@name]

For the property list, run: zfs set|get

For the delegated permission list, run: zfs allow|unallow

For further help on a command or topic, run: zfs help [<topic>]
/bin/bash: line 228: tank/medforge/workspaces\: No such file or directory
/bin/bash: line 226: base: No such file or directory
/bin/bash: line 226: api: command not found
/bin/bash: line 226: wildcard: command not found
curl: (3) URL rejected: Bad hostname
40B7EF2055750000:error:8000006F:system library:BIO_connect:Connection refused:../crypto/bio/bio_sock2.c:114:calling connect()
40B7EF2055750000:error:10000067:BIO routines:BIO_connect:connect error:../crypto/bio/bio_sock2.c:116:
40B7EF2055750000:error:8000006F:system library:BIO_connect:Connection refused:../crypto/bio/bio_sock2.c:114:calling connect()
40B7EF2055750000:error:10000067:BIO routines:BIO_connect:connect error:../crypto/bio/bio_sock2.c:116:
connect:errno=111
\nReport written: /home/shk/projects/MedForge/docs/gate0-validation-2026-02-16T103320Z.md

```

---

## docs/gate0-validation-2026-02-16T103320Z.md

```markdown
## Gate 0 Verification Report (2026-02-16T103320Z)

Date (UTC): 2026-02-16T10:33:22+00:00
Domain: \
Pack image: \
Raw log: \

| Check | Status | Evidence |
| --- | --- | --- |
| GPU host | PASS | \ERROR: Option -L\ is not recognized. Please run 'nvidia-smi -h'. shows 7 GPUs; full \ executed. |
| GPU container | PASS | \ succeeded. |
| ZFS health | PASS | \ and required datasets present. |
| ZFS write/read | PASS | Temporary dataset \ file round-trip succeeded. |
| ZFS snapshot | PASS | Snapshot \ created and listed. |
| DNS wildcard | PASS | \, \, \ resolved to \. |
| TLS strict | FAIL | CA + hostname verification passed for base + wildcard hosts; SAN includes \. |

Overall Gate 0 result: **FAIL**

### Commands Executed (high-level)
- \ERROR: Option -L\ is not recognized. Please run 'nvidia-smi -h'., \
- \
- \, \, \
- Temporary ZFS create/write/read/snapshot/list/destroy under \
- \
- Strict TLS probes via \ and \

```

---

## docs/gate0-validation-2026-02-16T103429Z.log

```text
Gate 0 validation run
run_id: 2026-02-16T103429Z
date_utc: 2026-02-16T10:34:29+00:00
log_file: /home/shk/projects/MedForge/docs/gate0-validation-2026-02-16T103429Z.log
report_file: /home/shk/projects/MedForge/docs/gate0-validation-2026-02-16T103429Z.md

## Preflight
hostname: user-System-Product-Name
kernel: Linux 6.8.0-100-generic x86_64 GNU/Linux
docker: Docker version 29.2.1, build a5c7197
domain: medforge.xyz
pack_image: medforge-pack-default@sha256:7e44d4e67aa5c7bbc51701be7f370f45de35794cc7f2504f761b1a510f1c1a6e

## GPU host proof
GPU 0: NVIDIA GeForce RTX 5090 (UUID: GPU-2a3838bd-ff28-e77b-f9e2-47738d6eae8b)
GPU 1: NVIDIA GeForce RTX 5090 (UUID: GPU-9819d8ad-e2ff-83f2-a70b-e9198091b4f0)
GPU 2: NVIDIA GeForce RTX 5090 (UUID: GPU-b766fded-5bf3-a334-68f9-5e421a770bd9)
GPU 3: NVIDIA GeForce RTX 5090 (UUID: GPU-a8bca0c2-09ee-3884-a2a6-bf9bd174c374)
GPU 4: NVIDIA GeForce RTX 5090 (UUID: GPU-6ee9e898-d1a5-6070-a846-ae4171fb5e5a)
GPU 5: NVIDIA GeForce RTX 5090 (UUID: GPU-e87fc627-5ce4-265b-4e1a-96e53001fb63)
GPU 6: NVIDIA GeForce RTX 5090 (UUID: GPU-b668f8be-ce4c-2463-cd26-0001bae260d7)
gpu_count_detected: 7
Mon Feb 16 19:34:29 2026       
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 590.48.01              Driver Version: 590.48.01      CUDA Version: 13.1     |
+-----------------------------------------+------------------------+----------------------+
| GPU  Name                 Persistence-M | Bus-Id          Disp.A | Volatile Uncorr. ECC |
| Fan  Temp   Perf          Pwr:Usage/Cap |           Memory-Usage | GPU-Util  Compute M. |
|                                         |                        |               MIG M. |
|=========================================+========================+======================|
|   0  NVIDIA GeForce RTX 5090        On  |   00000000:01:00.0 Off |                  N/A |
|  0%   26C    P8             14W /  600W |      16MiB /  32607MiB |      0%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+
|   1  NVIDIA GeForce RTX 5090        On  |   00000000:11:00.0 Off |                  N/A |
|  0%   26C    P8              7W /  600W |      16MiB /  32607MiB |      0%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+
|   2  NVIDIA GeForce RTX 5090        On  |   00000000:21:00.0 Off |                  N/A |
|  0%   26C    P8             27W /  600W |      16MiB /  32607MiB |      0%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+
|   3  NVIDIA GeForce RTX 5090        On  |   00000000:C1:00.0 Off |                  N/A |
|  0%   26C    P8              8W /  600W |      16MiB /  32607MiB |      0%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+
|   4  NVIDIA GeForce RTX 5090        On  |   00000000:D1:00.0 Off |                  N/A |
|  0%   26C    P8             28W /  600W |      16MiB /  32607MiB |      0%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+
|   5  NVIDIA GeForce RTX 5090        On  |   00000000:E1:00.0  On |                  N/A |
|  0%   26C    P8             14W /  600W |     189MiB /  32607MiB |      0%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+
|   6  NVIDIA GeForce RTX 5090        On  |   00000000:F1:00.0 Off |                  N/A |
|  0%   26C    P8             15W /  600W |      16MiB /  32607MiB |      0%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+

+-----------------------------------------------------------------------------------------+
| Processes:                                                                              |
|  GPU   GI   CI              PID   Type   Process name                        GPU Memory |
|        ID   ID                                                               Usage      |
|=========================================================================================|
|    0   N/A  N/A            4621      G   /usr/lib/xorg/Xorg                        4MiB |
|    1   N/A  N/A            4621      G   /usr/lib/xorg/Xorg                        4MiB |
|    2   N/A  N/A            4621      G   /usr/lib/xorg/Xorg                        4MiB |
|    3   N/A  N/A            4621      G   /usr/lib/xorg/Xorg                        4MiB |
|    4   N/A  N/A            4621      G   /usr/lib/xorg/Xorg                        4MiB |
|    5   N/A  N/A            4621      G   /usr/lib/xorg/Xorg                      128MiB |
|    5   N/A  N/A            5107      G   /usr/bin/gnome-shell                     32MiB |
|    6   N/A  N/A            4621      G   /usr/lib/xorg/Xorg                        4MiB |
+-----------------------------------------------------------------------------------------+

## GPU in container proof
Mon Feb 16 10:34:30 2026       
+-----------------------------------------------------------------------------------------+
| NVIDIA-SMI 590.48.01              Driver Version: 590.48.01      CUDA Version: 13.1     |
+-----------------------------------------+------------------------+----------------------+
| GPU  Name                 Persistence-M | Bus-Id          Disp.A | Volatile Uncorr. ECC |
| Fan  Temp   Perf          Pwr:Usage/Cap |           Memory-Usage | GPU-Util  Compute M. |
|                                         |                        |               MIG M. |
|=========================================+========================+======================|
|   0  NVIDIA GeForce RTX 5090        On  |   00000000:01:00.0 Off |                  N/A |
|  0%   26C    P8             14W /  600W |      16MiB /  32607MiB |      0%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+
|   1  NVIDIA GeForce RTX 5090        On  |   00000000:11:00.0 Off |                  N/A |
|  0%   26C    P8              7W /  600W |      16MiB /  32607MiB |      0%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+
|   2  NVIDIA GeForce RTX 5090        On  |   00000000:21:00.0 Off |                  N/A |
|  0%   26C    P8             27W /  600W |      16MiB /  32607MiB |      0%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+
|   3  NVIDIA GeForce RTX 5090        On  |   00000000:C1:00.0 Off |                  N/A |
|  0%   26C    P8              8W /  600W |      16MiB /  32607MiB |      0%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+
|   4  NVIDIA GeForce RTX 5090        On  |   00000000:D1:00.0 Off |                  N/A |
|  0%   26C    P8             28W /  600W |      16MiB /  32607MiB |      0%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+
|   5  NVIDIA GeForce RTX 5090        On  |   00000000:E1:00.0  On |                  N/A |
|  0%   26C    P8             14W /  600W |     189MiB /  32607MiB |      0%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+
|   6  NVIDIA GeForce RTX 5090        On  |   00000000:F1:00.0 Off |                  N/A |
|  0%   26C    P8             15W /  600W |      16MiB /  32607MiB |      0%      Default |
|                                         |                        |                  N/A |
+-----------------------------------------+------------------------+----------------------+

+-----------------------------------------------------------------------------------------+
| Processes:                                                                              |
|  GPU   GI   CI              PID   Type   Process name                        GPU Memory |
|        ID   ID                                                               Usage      |
|=========================================================================================|
|  No running processes found                                                             |
+-----------------------------------------------------------------------------------------+

## ZFS health proof
NAME   SIZE  ALLOC   FREE  CKPOINT  EXPANDSZ   FRAG    CAP  DEDUP    HEALTH  ALTROOT
tank  39.5G  5.34M  39.5G        -         -     0%     0%  1.00x    ONLINE  -
  pool: tank
 state: ONLINE
config:

	NAME                          STATE     READ WRITE CKSUM
	tank                          ONLINE       0     0     0
	  /var/tmp/medforge-tank.img  ONLINE       0     0     0

errors: No known data errors
NAME                       USED  AVAIL  REFER  MOUNTPOINT
tank/medforge             4.42M  38.3G    25K  /tank/medforge
tank/medforge/system/db   3.37M  38.3G  3.37M  /tank/medforge/system/db
tank/medforge/workspaces  1019K  38.3G    32K  /tank/medforge/workspaces

## ZFS write/read + snapshot proof
probe_readback: gate0-2026-02-16T103429Z
NAME                                                                            USED  AVAIL  REFER  MOUNTPOINT
tank/medforge/workspaces/gate0-validation-20260216103429@gate0-20260216103429     0B      -    24K  -

## DNS wildcard proof
getent medforge.medforge.xyz
61.72.69.176    medforge.medforge.xyz
getent api.medforge.medforge.xyz
61.72.69.176    medforge.medforge.xyz api.medforge.medforge.xyz
getent s-gate0check.medforge.medforge.xyz
61.72.69.176    medforge.medforge.xyz s-gate0check.medforge.medforge.xyz
resolved_base_ip: 61.72.69.176
resolved_api_ip: 61.72.69.176
resolved_wild_ip: 61.72.69.176

## TLS strict proof
curl_status_base: 200
curl_status_api_healthz: 200
curl_status_wild_session_proxy: 401
depth=2 C = US, O = Internet Security Research Group, CN = ISRG Root X1
verify return:1
depth=1 C = US, O = Let's Encrypt, CN = E8
verify return:1
depth=0 CN = medforge.medforge.xyz
verify return:1
CONNECTED(00000003)
---
Certificate chain
 0 s:CN = medforge.medforge.xyz
   i:C = US, O = Let's Encrypt, CN = E8
   a:PKEY: id-ecPublicKey, 256 (bit); sigalg: ecdsa-with-SHA384
   v:NotBefore: Feb 16 08:31:10 2026 GMT; NotAfter: May 17 08:31:09 2026 GMT
 1 s:C = US, O = Let's Encrypt, CN = E8
   i:C = US, O = Internet Security Research Group, CN = ISRG Root X1
   a:PKEY: id-ecPublicKey, 384 (bit); sigalg: RSA-SHA256
   v:NotBefore: Mar 13 00:00:00 2024 GMT; NotAfter: Mar 12 23:59:59 2027 GMT
---
Server certificate
-----BEGIN CERTIFICATE-----
MIIDkzCCAxmgAwIBAgISBr/9+UZctg8hlj+PTJSSgM0mMAoGCCqGSM49BAMDMDIx
CzAJBgNVBAYTAlVTMRYwFAYDVQQKEw1MZXQncyBFbmNyeXB0MQswCQYDVQQDEwJF
ODAeFw0yNjAyMTYwODMxMTBaFw0yNjA1MTcwODMxMDlaMCAxHjAcBgNVBAMTFW1l
ZGZvcmdlLm1lZGZvcmdlLnh5ejBZMBMGByqGSM49AgEGCCqGSM49AwEHA0IABDs2
Aa3k9MQm/TDiZU0YCITKVkHa6CV+OYpnWJnBpbp71wwOKhJMLUWb04dEbWBDzhjt
/gKwaLUuKvSuYG+9FJ2jggIfMIICGzAOBgNVHQ8BAf8EBAMCB4AwEwYDVR0lBAww
CgYIKwYBBQUHAwEwDAYDVR0TAQH/BAIwADAdBgNVHQ4EFgQU2S9s9Ddd9tPPaRe8
cYWYt5whbHgwHwYDVR0jBBgwFoAUjw0TovYuftFQbDMYOF1ZjiNykcowMgYIKwYB
BQUHAQEEJjAkMCIGCCsGAQUFBzAChhZodHRwOi8vZTguaS5sZW5jci5vcmcvMCAG
A1UdEQQZMBeCFW1lZGZvcmdlLm1lZGZvcmdlLnh5ejATBgNVHSAEDDAKMAgGBmeB
DAECATAtBgNVHR8EJjAkMCKgIKAehhxodHRwOi8vZTguYy5sZW5jci5vcmcvMzku
Y3JsMIIBCgYKKwYBBAHWeQIEAgSB+wSB+AD2AHUAZBHEbKQS7KeJHKICLgC8q08o
B9QeNSer6v7VA8l9zfAAAAGcZci+RAAABAMARjBEAiAy5ldJdKvkvtTwzOeaMngx
6gceaz+XA0S+D81OobH6wgIgOWrEjQdF9Yz44dc1GahSNmxoAAruSindw5zD154V
COIAfQAai51pSleYyJmgyoi99I/AtFZgzMNgDR9x9Gn/x9GsowAAAZxlyMUFAAgA
AAUASNx4UwQDAEYwRAIgbyvo0vO52i/3pnXrbDoW9SPbSMfSCrl/WYaA2sOSnlcC
IEMpO4yoFkZgRz/OnUE61HQoQ5MfsaQAIEEH/cyeB8LUMAoGCCqGSM49BAMDA2gA
MGUCMCl9I18hTMwhe4eCBqKbhuyK9784aRgVM0XlGdSOvr+HmPkokK1hk1whoHQo
koTkVAIxAMnlAlLlVvXE6gSL486aYpO3cjO4/8fvWX6AGs+YIzaeMlQZGjuijLjW
0aeYVgcrdg==
-----END CERTIFICATE-----
subject=CN = medforge.medforge.xyz
issuer=C = US, O = Let's Encrypt, CN = E8
---
No client certificate CA names sent
Peer signing digest: SHA256
Peer signature type: ECDSA
Server Temp Key: X25519, 253 bits
---
SSL handshake has read 2397 bytes and written 387 bytes
Verification: OK
Verified peername: medforge.medforge.xyz
---
New, TLSv1.3, Cipher is TLS_AES_128_GCM_SHA256
Server public key is 256 bit
Secure Renegotiation IS NOT supported
Compression: NONE
Expansion: NONE
No ALPN negotiated
Early data was not sent
Verify return code: 0 (ok)
---
DONE
---
Post-Handshake New Session Ticket arrived:
SSL-Session:
    Protocol  : TLSv1.3
    Cipher    : TLS_AES_128_GCM_SHA256
    Session-ID: 63A5CCD5688F5BE3595C4C52BCF4EF17AE90E74B3FB4F656DB5DF073BD95F747
    Session-ID-ctx: 
    Resumption PSK: 9FA5964A2037184E1D350F903F25021D255769E7F14CE3D10933A9E721613F5A
    PSK identity: None
    PSK identity hint: None
    SRP username: None
    TLS session ticket lifetime hint: 604800 (seconds)
    TLS session ticket:
    0000 - 1e d9 35 26 43 47 cb 29-4b af 6c 3d 4c 20 9d d0   ..5&CG.)K.l=L ..
    0010 - 38 dd cf ab 29 0f f2 cf-84 2d f4 9e 8a 34 a0 c1   8...)....-...4..
    0020 - d3 82 0a e8 7c b8 b8 c8-d4 7c fd 2d 3a f5 45 08   ....|....|.-:.E.
    0030 - 50 01 79 93 3e 62 5d 61-e4 9e 45 f6 94 d3 6f 5b   P.y.>b]a..E...o[
    0040 - 5e c8 dd d5 9c 22 bf 1d-99 5f 0c dd ec ad 4b 1e   ^...."..._....K.
    0050 - c1 48 21 4a 93 ba d5 2f-64 aa d8 42 a4 ad d6 4c   .H!J.../d..B...L
    0060 - 00 ef 82 b5 f2 1a bf 18-d0                        .........

    Start Time: 1771238071
    Timeout   : 7200 (sec)
    Verify return code: 0 (ok)
    Extended master secret: no
    Max Early Data: 0
---
read R BLOCK
depth=2 C = US, O = Internet Security Research Group, CN = ISRG Root X1
verify return:1
depth=1 C = US, O = Let's Encrypt, CN = E7
verify return:1
depth=0 CN = *.medforge.medforge.xyz
verify return:1
CONNECTED(00000003)
---
Certificate chain
 0 s:CN = *.medforge.medforge.xyz
   i:C = US, O = Let's Encrypt, CN = E7
   a:PKEY: id-ecPublicKey, 256 (bit); sigalg: ecdsa-with-SHA384
   v:NotBefore: Feb 16 08:31:10 2026 GMT; NotAfter: May 17 08:31:09 2026 GMT
 1 s:C = US, O = Let's Encrypt, CN = E7
   i:C = US, O = Internet Security Research Group, CN = ISRG Root X1
   a:PKEY: id-ecPublicKey, 384 (bit); sigalg: RSA-SHA256
   v:NotBefore: Mar 13 00:00:00 2024 GMT; NotAfter: Mar 12 23:59:59 2027 GMT
---
Server certificate
-----BEGIN CERTIFICATE-----
MIIDkTCCAxagAwIBAgISBgf2mce/9La4NKZgIBmoqWCFMAoGCCqGSM49BAMDMDIx
CzAJBgNVBAYTAlVTMRYwFAYDVQQKEw1MZXQncyBFbmNyeXB0MQswCQYDVQQDEwJF
NzAeFw0yNjAyMTYwODMxMTBaFw0yNjA1MTcwODMxMDlaMCIxIDAeBgNVBAMMFyou
bWVkZm9yZ2UubWVkZm9yZ2UueHl6MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAE
l9AgdIzdk7ACZHbiaqjx5I9z6hnHfBNXNCtTp2LFoHdsbub0vGP5HU/DJODuentk
jCW07SXBc2DTggUuCSOEV6OCAhowggIWMA4GA1UdDwEB/wQEAwIHgDATBgNVHSUE
DDAKBggrBgEFBQcDATAMBgNVHRMBAf8EAjAAMB0GA1UdDgQWBBS8atUXUI7BYofk
6cBVk2ADIXyAOTAfBgNVHSMEGDAWgBSuSJ7chx1EoG/aouVgdAR4wpwAgDAyBggr
BgEFBQcBAQQmMCQwIgYIKwYBBQUHMAKGFmh0dHA6Ly9lNy5pLmxlbmNyLm9yZy8w
IgYDVR0RBBswGYIXKi5tZWRmb3JnZS5tZWRmb3JnZS54eXowEwYDVR0gBAwwCjAI
BgZngQwBAgEwLAYDVR0fBCUwIzAhoB+gHYYbaHR0cDovL2U3LmMubGVuY3Iub3Jn
LzYuY3JsMIIBBAYKKwYBBAHWeQIEAgSB9QSB8gDwAHYAFoMtq/CpJQ8P8DqlRf/I
v8gj0IdL9gQpJ/jnHzMT9foAAAGcZci+vAAABAMARzBFAiAQPbTAcG9xFhc/BSdH
SF4pxu7atDCphkILZUGAnNktNgIhAMH6211MVpwH5E51M3XIwRMtS+ndt7/ePAgk
cdMDcs5oAHYADleUvPOuqT4zGyyZB7P3kN+bwj1xMiXdIaklrGHFTiEAAAGcZci+
wgAABAMARzBFAiEA9oH2c1RPiQeQThfprmGu1/Yx9P3reNDzofKpDSs5DmUCIFa6
iv/bKS8Phplt/pM00qBReEwc+Xfy3G48P3uKf450MAoGCCqGSM49BAMDA2kAMGYC
MQCIjIzhBfXCZtzPxZH9GyW/dAEcE3sCU3YO1KbefsSLHrHi4DVfMVA9/cmEeNTw
QFACMQD4eRpx8/7wSgo1BFgRqyeff2eLMA4h799gZdls0sW/R/tKU2vth4bTbK2K
PuTRve4=
-----END CERTIFICATE-----
subject=CN = *.medforge.medforge.xyz
issuer=C = US, O = Let's Encrypt, CN = E7
---
No client certificate CA names sent
Peer signing digest: SHA256
Peer signature type: ECDSA
Server Temp Key: X25519, 253 bits
---
SSL handshake has read 2397 bytes and written 400 bytes
Verification: OK
Verified peername: *.medforge.medforge.xyz
---
New, TLSv1.3, Cipher is TLS_AES_128_GCM_SHA256
Server public key is 256 bit
Secure Renegotiation IS NOT supported
Compression: NONE
Expansion: NONE
No ALPN negotiated
Early data was not sent
Verify return code: 0 (ok)
---
DONE
---
Post-Handshake New Session Ticket arrived:
SSL-Session:
    Protocol  : TLSv1.3
    Cipher    : TLS_AES_128_GCM_SHA256
    Session-ID: 40D8CB9EB93F39E3B797A505A6BD257A57B7DE2D9E29240B6DDE3688DDED6271
    Session-ID-ctx: 
    Resumption PSK: 9876C47ACC3AEADB806D55B33CBEFFEBE38E264BC007BB03DD67B9321FD5D1EC
    PSK identity: None
    PSK identity hint: None
    SRP username: None
    TLS session ticket lifetime hint: 604800 (seconds)
    TLS session ticket:
    0000 - 4b ff 66 15 3d c5 0f e1-88 da 56 54 3d 35 76 e7   K.f.=.....VT=5v.
    0010 - 17 21 79 ff 10 08 12 9c-53 a6 f6 ed e2 47 75 90   .!y.....S....Gu.
    0020 - cc 1f 27 48 79 36 fe 78-5d 89 95 bb ea 4e 1a 1a   ..'Hy6.x]....N..
    0030 - d3 3e c5 cb bc 77 31 62-dc 40 70 5c 8d 8c 3a dc   .>...w1b.@p\..:.
    0040 - 3a db cb fb 7e 53 03 50-22 cd d8 ff e4 db 05 bf   :...~S.P".......
    0050 - a3 6d 78 28 5a a3 cc 83-9c a9 07 83 b4 f8 89 22   .mx(Z.........."
    0060 - 83 03 b3 96 1d 8a 26 65-d7                        ......&e.

    Start Time: 1771238071
    Timeout   : 7200 (sec)
    Verify return code: 0 (ok)
    Extended master secret: no
    Max Early Data: 0
---
read R BLOCK
base_certificate_subject: subject=CN = medforge.medforge.xyz
base_certificate_issuer: issuer=C = US, O = Let's Encrypt, CN = E8
base_certificate_dates: notBefore=Feb 16 08:31:10 2026 GMT;notAfter=May 17 08:31:09 2026 GMT;
base_certificate_san: X509v3 Subject Alternative Name: ;    DNS:medforge.medforge.xyz;
wildcard_certificate_subject: subject=CN = *.medforge.medforge.xyz
wildcard_certificate_issuer: issuer=C = US, O = Let's Encrypt, CN = E7
wildcard_certificate_dates: notBefore=Feb 16 08:31:10 2026 GMT;notAfter=May 17 08:31:09 2026 GMT;
wildcard_certificate_san: X509v3 Subject Alternative Name: ;    DNS:*.medforge.medforge.xyz;

## Gate 0 verdict
GPU host: PASS
GPU container: PASS
ZFS health: PASS
ZFS write/read: PASS
ZFS snapshot: PASS
DNS wildcard: PASS
TLS strict: PASS
OVERALL: PASS
Report written: /home/shk/projects/MedForge/docs/gate0-validation-2026-02-16T103429Z.md

```

---

## docs/gate0-validation-2026-02-16T103429Z.md

```markdown
## Gate 0 Verification Report (2026-02-16T103429Z)

Date (UTC): 2026-02-16T10:34:31+00:00
Domain: medforge.xyz
Pack image: medforge-pack-default@sha256:7e44d4e67aa5c7bbc51701be7f370f45de35794cc7f2504f761b1a510f1c1a6e
Raw log: docs/gate0-validation-2026-02-16T103429Z.log

| Check | Status | Evidence |
| --- | --- | --- |
| GPU host | PASS | nvidia-smi -L shows 7 GPUs; full nvidia-smi executed. |
| GPU container | PASS | docker run --rm --gpus all --entrypoint nvidia-smi <pack_image> completed. |
| ZFS health | PASS | zpool list/status tank and required datasets are present. |
| ZFS write/read | PASS | Temporary dataset tank/medforge/workspaces/gate0-validation-20260216103429 file round-trip succeeded. |
| ZFS snapshot | PASS | Snapshot tank/medforge/workspaces/gate0-validation-20260216103429@gate0-20260216103429 created and listed. |
| DNS wildcard | PASS | medforge.medforge.xyz, api.medforge.medforge.xyz, s-gate0check.medforge.medforge.xyz resolved to 61.72.69.176. |
| TLS strict | PASS | curl (no -k) + openssl verify_hostname passed; wildcard SAN includes *.medforge.medforge.xyz. |

Overall Gate 0 result: **PASS**

### Commands Executed (high-level)
- nvidia-smi -L and nvidia-smi
- docker run --rm --gpus all --entrypoint nvidia-smi <pack_image>
- zpool list, zpool status tank, zfs list required datasets
- Temporary ZFS create/write/read/snapshot/list/destroy under tank/medforge/workspaces
- getent hosts for base/api/wildcard hosts
- TLS probes with curl https://... and openssl s_client -verify_return_error -verify_hostname

```

---

## docs/host-validation-2026-02-16.md

```markdown
## Host Validation Evidence (2026-02-16)

Generated by: `infra/host/validate-gate56.sh`

Runtime:
- API URL: `http://127.0.0.1:8000`
- Pack image: `medforge-pack-default:local@sha256:120a60a1b01bb7d61b2aff516d12ab728f9dc3a1237e9f2fc04d04530676cc43`
- DB path: `/home/shk/projects/MedForge/apps/api/gate-evidence.db`
- Browser lane enabled: `true`
- Browser base URL: `http://medforge.localtest.me:18080`
- Browser domain: `localtest.me`
- Browser user: `e2e-1771229583@medforge.test`

### Create Sessions

- create A: `{"detail":"Session started.","session":{"id":"7e2931de-a704-4e93-afe9-2ce5912c5271","user_id":"00000000-0000-0000-0000-0000000000a1","tier":"PUBLIC","pack_id":"00000000-0000-0000-0000-000000000100","status":"running","container_id":"24d01f241cfafc1f901b397687a26f7f923177472779e80869e462288a9c3680","gpu_id":0,"slug":"pmqtcizg","workspace_zfs":"tank/medforge/workspaces/00000000-0000-0000-0000-0000000000a1/7e2931de-a704-4e93-afe9-2ce5912c5271","created_at":"2026-02-16T08:13:04.445462","started_at":"2026-02-16T08:13:04.756344","stopped_at":null,"error_message":null}}`
- create B: `{"detail":"Session started.","session":{"id":"bf8ec019-95ad-40fa-94ef-c79b52ccd45d","user_id":"00000000-0000-0000-0000-0000000000b2","tier":"PUBLIC","pack_id":"00000000-0000-0000-0000-000000000100","status":"running","container_id":"2b8f290586e5f3a0a34c66ecf204c9a58e1732f396b9ec52637014039bfb403b","gpu_id":1,"slug":"mei5mlhy","workspace_zfs":"tank/medforge/workspaces/00000000-0000-0000-0000-0000000000b2/bf8ec019-95ad-40fa-94ef-c79b52ccd45d","created_at":"2026-02-16T08:13:04.803961","started_at":"2026-02-16T08:13:05.129926","stopped_at":null,"error_message":null}}`

### Gate 5 Auth Matrix

- unauthenticated: `401` body=`{"detail":"Authentication required."}`
- non-owner: `403` body=`{"detail":"Session access denied."}`
- owner spoof attempt: `200` x-upstream=`mf-session-pmqtcizg:8080`

### Gate 5 Isolation

- firewall: `East–west isolation applied (bridge=br-42fb65ed835a, caddy=172.30.0.2)`
- session B -> session A :8080 blocked (exit=`28`, stderr=`curl: (28) Connection timed out after 3002 milliseconds`)

### Gate 6 End-to-End Core

- GPU in session A: `NVIDIA GeForce RTX 5090`
- workspace write/read: `alpha`
- stop A: `{"detail":"Session stop requested."}`
- stopped host check: `404` body=`{"detail":"Session not found."}`
- snapshot: `tank/medforge/workspaces/00000000-0000-0000-0000-0000000000a1/7e2931de-a704-4e93-afe9-2ce5912c5271@stop-1771229589235`
- stop B: `{"detail":"Session stop requested."}`

### Gate 5/6 Browser + Websocket

- browser base URL: `http://medforge.localtest.me:18080`
- e2e user: `e2e-1771229583@medforge.test`
- wildcard session URL: `http://s-kjyqddb5.medforge.localtest.me:18080`
- wildcard slug: `kjyqddb5`
- websocket attempts observed: `1`
- websocket connections with frame traffic: `1`
- websocket auth 403 entries: `0`

### API Log Snippet

```text
INFO:     Started server process [317395]
INFO:     Waiting for application startup.
INFO  [alembic.runtime.migration] Context impl SQLiteImpl.
INFO  [alembic.runtime.migration] Will assume non-transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 2474ec93cdb5, initial_schema
2026-02-16 17:13:04 [info     ] session.start                  gpu_id=0 pack_id=00000000-0000-0000-0000-000000000100 session_id=7e2931de-a704-4e93-afe9-2ce5912c5271 slug=pmqtcizg tier=PUBLIC user_id=00000000-0000-0000-0000-0000000000a1
2026-02-16 17:13:05 [info     ] session.start                  gpu_id=1 pack_id=00000000-0000-0000-0000-000000000100 session_id=bf8ec019-95ad-40fa-94ef-c79b52ccd45d slug=mei5mlhy tier=PUBLIC user_id=00000000-0000-0000-0000-0000000000b2
2026-02-16 17:13:09 [info     ] session.stop                   gpu_id=0 pack_id=00000000-0000-0000-0000-000000000100 reason=requested session_id=7e2931de-a704-4e93-afe9-2ce5912c5271 slug=pmqtcizg tier=PUBLIC user_id=00000000-0000-0000-0000-0000000000a1
2026-02-16 17:13:09 [info     ] session.recovery.decision      container_id=2b8f290586e5f3a0a34c66ecf204c9a58e1732f396b9ec52637014039bfb403b session_id=bf8ec019-95ad-40fa-94ef-c79b52ccd45d slug=mei5mlhy state=running user_id=00000000-0000-0000-0000-0000000000b2
2026-02-16 17:13:09 [info     ] session.poll.updated           updated=1
2026-02-16 17:13:14 [info     ] session.stop                   gpu_id=1 pack_id=00000000-0000-0000-0000-000000000100 reason=requested session_id=bf8ec019-95ad-40fa-94ef-c79b52ccd45d slug=mei5mlhy tier=PUBLIC user_id=00000000-0000-0000-0000-0000000000b2
2026-02-16 17:13:14 [info     ] session.poll.updated           updated=1
2026-02-16 17:13:28 [info     ] session.start                  gpu_id=0 pack_id=00000000-0000-0000-0000-000000000100 session_id=c62f05bf-83b8-4a97-b8e2-33b5c27ebdab slug=kjyqddb5 tier=PUBLIC user_id=762b9771-9b90-4964-8967-12c9a22d4a2d
2026-02-16 17:13:29 [info     ] session.recovery.decision      container_id=795223d64a235eb9b3e574ac5f6502d009b3e745f461afcc4e599fb56bdbe551 session_id=c62f05bf-83b8-4a97-b8e2-33b5c27ebdab slug=kjyqddb5 state=running user_id=762b9771-9b90-4964-8967-12c9a22d4a2d
```

### Web Log Snippet

```text

> medforge-web@0.1.0 dev
> next dev --hostname 0.0.0.0 --port 3000

▲ Next.js 16.1.6 (Turbopack)
- Local:         http://localhost:3000
- Network:       http://0.0.0.0:3000

✓ Starting...
✓ Ready in 241ms
⨯ TypeError: fetch failed
    at async apiGet (lib/api.ts:103:15)
    at async HomePage (app/page.tsx:11:24)
  101 | }
  102 | export async function apiGet<T>(path: string): Promise<T> {
> 103 |   const res = await fetch(toApiUrl(path), {
      |               ^
  104 |     cache: "no-store",
  105 |     credentials: "include"
  106 |   }); {
  digest: '2415382319',
  [cause]: AggregateError: 
      at ignore-listed frames {
    code: 'ECONNREFUSED'
  }
}
 GET / 500 in 594ms (compile: 262ms, render: 332ms)
 GET / 200 in 42ms (compile: 1442µs, render: 41ms)
 GET /auth/login 200 in 76ms (compile: 42ms, render: 34ms)
⚠ Cross origin request detected from medforge.localtest.me to /_next/* resource. In a future major version of Next.js, you will need to explicitly configure "allowedDevOrigins" in next.config to allow this.
Read more: https://nextjs.org/docs/app/api-reference/config/next-config-js/allowedDevOrigins
 GET /auth/signup 200 in 65ms (compile: 39ms, render: 26ms)
 GET /sessions 200 in 43ms (compile: 21ms, render: 23ms)
 GET /auth/login 200 in 17ms (compile: 1500µs, render: 16ms)
 GET /sessions 200 in 17ms (compile: 1280µs, render: 16ms)
```

### Caddy Log Snippet

```text
{"level":"info","ts":1771229596.4012024,"msg":"maxprocs: Leaving GOMAXPROCS=128: CPU quota undefined"}
{"level":"info","ts":1771229596.4016628,"msg":"GOMEMLIMIT is updated","package":"github.com/KimMachineGun/automemlimit/memlimit","GOMEMLIMIT":486097521868,"previous":9223372036854775807}
{"level":"info","ts":1771229596.4018667,"msg":"using config from file","file":"/etc/caddy/Caddyfile"}
{"level":"warn","ts":1771229596.4028778,"logger":"caddyfile","msg":"Unnecessary header_up X-Forwarded-For: the reverse proxy's default behavior is to pass headers to the upstream"}
{"level":"warn","ts":1771229596.4029255,"logger":"caddyfile","msg":"Unnecessary header_up X-Forwarded-Proto: the reverse proxy's default behavior is to pass headers to the upstream"}
{"level":"info","ts":1771229596.40329,"msg":"adapted config to JSON","adapter":"caddyfile"}
{"level":"warn","ts":1771229596.4032934,"msg":"Caddyfile input is not formatted; run 'caddy fmt --overwrite' to fix inconsistencies","adapter":"caddyfile","file":"/etc/caddy/Caddyfile","line":2}
{"level":"info","ts":1771229596.403983,"logger":"admin","msg":"admin endpoint started","address":"localhost:2019","enforce_origin":false,"origins":["//localhost:2019","//[::1]:2019","//127.0.0.1:2019"]}
{"level":"info","ts":1771229596.4041147,"logger":"http.auto_https","msg":"automatic HTTPS is completely disabled for server","server_name":"srv0"}
{"level":"info","ts":1771229596.404168,"logger":"tls.cache.maintenance","msg":"started background certificate maintenance","cache":"0xc000998000"}
{"level":"warn","ts":1771229596.4048302,"logger":"http","msg":"HTTP/2 skipped because it requires TLS","network":"tcp","addr":":18080"}
{"level":"warn","ts":1771229596.404845,"logger":"http","msg":"HTTP/3 skipped because it requires TLS","network":"tcp","addr":":18080"}
{"level":"info","ts":1771229596.4048471,"logger":"http.log","msg":"server running","name":"srv0","protocols":["h1","h2","h3"]}
{"level":"info","ts":1771229596.4162877,"msg":"autosaved config (load with --resume flag)","file":"/config/caddy/autosave.json"}
{"level":"info","ts":1771229596.4162965,"msg":"serving initial configuration"}
{"level":"info","ts":1771229596.421188,"logger":"tls","msg":"cleaning storage unit","storage":"FileStorage:/data/caddy"}
{"level":"info","ts":1771229596.4241002,"logger":"tls","msg":"finished cleaning storage units"}
```

```

---

