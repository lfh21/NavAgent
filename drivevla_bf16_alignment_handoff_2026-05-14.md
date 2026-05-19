# DriveVLA BF16 TRT 对齐交接记录

日期：2026-05-14  
本地工作区：`/Users/liangfenghe/Documents/New project`  
远端目标机：`ssh -p 2222 root@172.31.15.61`  
远端仓库：`/root/code/drivevla`

## 1. 用户目标

目标是解决 `streaming_v2` 轨迹模型从 ONNX 转 TensorRT `bf16` 后无法和 dump/Torch 对齐的问题。  
用户给出的关键路径：

- dump：`/iag_ad_vepfs_volc/iag_ad_vepfs_volc/liangfenghe/dump/full_forward_dump.pb`
- ONNX 目录：`/iag_ad_vepfs_volc/iag_ad_vepfs_volc/liangfenghe/trajectory_mlp_fp32/step_24800_reexport_merge_66a4f32_fix5_explicit_suffix`
- 目标 ONNX：`/iag_ad_vepfs_volc/iag_ad_vepfs_volc/liangfenghe/trajectory_mlp_fp32/step_24800_reexport_merge_66a4f32_fix5_explicit_suffix/trajectory_mlp_e2e_v2_debug.onnx`
- Torch ckpt：`/iag_ad_vepfs_volc/iag_ad_vepfs_volc/liangfenghe/trajectory_mlp_fp32/torch_ckpt`
- 重点脚本：`/root/code/drivevla/scripts/export_trajectory_mlp_onnx.py`

## 2. 已确认的事实

### 2.1 远端仓库状态

开始时远端 `git status --short` 显示：

- `M scripts/export_trajectory_mlp_onnx.py`
- `M scripts/onnx_alignment_streaming_v2.py`
- `?? scripts/trt_alignment_streaming_v2.py`

说明仓库本来就是脏工作区，不要盲目覆盖。

### 2.2 当前 ONNX 最初确实缺少 precision metadata

对目标 ONNX 的第一次检查结果：

- `has_precision_policy = False`
- `node_precision_hint_count = 0`

也就是说，用户说的“导出的 ONNX 缺少 precision_hint”这件事一开始是真实成立的。

### 2.3 真正走到这次导出路径的是 `export_streaming_v2 + export_debug_model`

从远端 hydra 输出可确认，这次产物来自：

- `outputs/2026-05-14/07-09-21/.hydra/config.yaml`

关键配置：

- `export_streaming_v2=true`
- `export_debug_model=true`
- `mode=combined`
- `output_dir=/iag_ad_vepfs_volc/iag_ad_vepfs_volc/liangfenghe/trajectory_mlp_fp32/step_24800_reexport_merge_66a4f32_fix5_explicit_suffix`

这点很重要：  
不是 `export_combined_v2` 路径，而是 `export_combined_trajectory_model_streaming_v2()` 这条分支。

## 3. 关键根因定位

### 3.1 `export_combined_trajectory_model_streaming_v2()` 当时没有调用 `_annotate_onnx_precision_policy()`

检查远端源码后确认：

- `export_combined_v2` 分支末尾会调 `_annotate_onnx_precision_policy(output_path, has_kinematic_rollout=True)`
- `export_combined_trajectory_model_streaming_v2()` 原来直接 `return output_path`

所以这次 `trajectory_mlp_e2e_v2_debug.onnx` 没有任何 `precision_hint`/`precision_policy` 的直接原因，就是 streaming_v2 导出分支漏调注释函数。

### 3.2 `scripts/trt_alignment_streaming_v2.py` 当时也没有真正消费 precision metadata

检查该脚本发现它原来有两个问题：

- 直接用 `parser.parse(f.read())`，不是 `parse_from_file()`，对 external data 更脆弱
- BF16 build 时没有复用 `scripts/convert_onnx_to_trt_v2.py` 里的 `_apply_fp32_layer_precision_from_onnx_metadata()`

后面我已经把这两个点改进过一次，见“第 4 节”。

## 4. 本轮已经实际落到远端的代码改动

以下改动已经确认写到远端：

### 4.1 `scripts/export_trajectory_mlp_onnx.py`

已确认落地：

- 修掉 `export_combined_trajectory_model_v2()` 里重复调用 `_annotate_onnx_precision_policy()` 的重复行
- 在 `export_combined_trajectory_model_streaming_v2()` 末尾加入：
  - `print(f"[export_streaming_v2] exported to {output_path}")`
  - `_annotate_onnx_precision_policy(output_path, has_kinematic_rollout=True)`

也就是说，后续重新导 streaming_v2 debug ONNX 时，会自动写 precision metadata。

### 4.2 `scripts/trt_alignment_streaming_v2.py`

已确认落地：

- 增加 `import convert_onnx_to_trt_v2 as trt_convert_utils`
- 增加 `from pprint import pformat`
- 将 ONNX 解析从 `parser.parse(f.read())` 改为 `parser.parse_from_file(str(onnx_path))`
- 在 BF16 build 前调用：
  - `trt_convert_utils._apply_fp32_layer_precision_from_onnx_metadata(...)`
- 会打印：
  - `fp32_override_summary`

注意：

- 这个脚本当前仍然是“早期改动版本”
- 我后面想继续把它升级为 “OBEY + subgraph pattern” 版本，但那一步被用户中断，没有落地

## 5. 当前 ONNX 头部状态

### 5.1 已经对现有 ONNX 做过一次正式注释

我对现有 ONNX 运行过：

```python
_annotate_onnx_precision_policy(
    trajectory_mlp_e2e_v2_debug.onnx,
    has_kinematic_rollout=True,
)
```

第一次正式注释的输出是：

- `annotated 402 fp32 node(s)`

随后复查结果：

- `has_precision_policy = True`
- `meta_version = 1.1`
- `meta_fp32_nodes = 402`
- `node_precision_hint_count = 402`
- `pattern_count = 9`

### 5.2 后续调试实验又在同一个 ONNX 头里额外加过 hint

为了定位问题，我又做了两次“原地加 hint”的实验：

- `RMSNorm full chain`：额外加了 `113` 个节点
- `all MatMul`：额外加了 `259` 个节点

所以当前这份 ONNX 头里的真实 `precision_hint=fp32` 节点数已经不是 402，而是更高。  
后面实验里 `_apply_fp32_layer_precision_from_onnx_metadata()` 扫出来的是：

- `fp32_annotated = 774`

但要注意：

- `metadata_props["precision_policy"]` 很可能还是最初那份 `version=1.1` / `fp32_nodes=402` / `pattern_count=9`
- 也就是说：当前 ONNX 的“逐节点 attribute”和“model-level precision_policy JSON”已经不完全同步

如果后续要整理干净，建议：

1. 先把代码修到位
2. 再重新导一次 ONNX 或重新跑一次正式 `_annotate_onnx_precision_policy()`，避免继续在历史头上叠加实验性 attribute

## 6. 验证结果总表

### 6.1 基线：同一套 TRT 对齐脚本下，FP32 是正常对齐的

命令使用现成 engine：

- engine：`trajectory_mlp_e2e_v2_debug.fp32.trt`

结果：

- `samples=3`
- `passed=3/3`
- golden sample：
  - `cos_acc=0.999999`
  - `cos_yaw_rate=0.999999`

结论：

- `scripts/trt_alignment_streaming_v2.py` 这条验证链本身没有根本性错误
- BF16 问题是真实的 BF16 精度问题，不是验证脚本本身的假阳性

### 6.2 仅靠最初 402 个 hint 的 BF16 engine：失败

使用注释后的 ONNX 和改过的 `trt_alignment_streaming_v2.py`，重建新 engine：

- engine：`trajectory_mlp_e2e_v2_debug.precision_hint.bf16.trt`
- report：`trajectory_mlp_e2e_v2_debug.precision_hint.bf16.alignment.html`

构建日志中的关键点：

- `ONNX nodes with precision_hint=fp32: 374`
- `skipped op types (FMHA mode): Softmax×28`
- `FP32 precision applied to 374 / 9592 layers`

10 样本结果：

- `passed=0/10`
- 首样本：
  - `cos_acc=0.781513`
  - `cos_yaw_rate=0.855867`

结论：

- “把缺失的 precision_hint 补回来”可以修正导出链，但不足以让 BF16 对齐

### 6.3 中间输出定位：真正开始炸的是 `plan_query_hidden`

对比 FP32 TRT vs BF16 TRT 的 debug outputs，首样本大致如下：

- `nav_embeds`: 小偏差
- `inputs_embeds_before_visual`: 很小
- `full_video_embeds`: 很小
- `inputs_embeds`: 很小
- `plan_query_hidden`: `max_abs=22.688...`, `mean_abs=1.357...`
- `actions`: 明显炸
- `trajectory`: 明显炸

结论：

- 问题不在 nav/video 拼接
- 主要误差在 `language_model` 主干内部累积

### 6.4 失败/无效的实验

这些实验都做过，但对齐没有本质改善：

1. 让 `Softmax` 也保持 FP32
2. 把 RMSNorm 全链 `Cast/Pow/ReduceMean/...` 都补成 FP32 hint
3. 把所有 `MatMul` 节点都补成 FP32 hint
4. 只靠旧的 `trt_layer_name_patterns`
5. `PREFER_PRECISION_CONSTRAINTS`
6. `OBEY_PRECISION_CONSTRAINTS` 但仍只依赖旧 hint/pattern

这些实验说明：

- 问题不是单个 op type 少了几个 hint
- 而是需要把更大范围的子图整体钉回 FP32

### 6.5 边界实验：把所有浮点 layer 都钉成 FP32，BF16 立刻接近通过

实验 engine：

- `trajectory_mlp_e2e_v2_debug.all_layers_fp32.bf16.trt`

方法：

- parse 后，对所有“输出 dtype 为 FLOAT/HALF/BF16”的 layer 直接 `layer.precision = FLOAT`
- build flag 使用：
  - `BF16`
  - `OBEY_PRECISION_CONSTRAINTS`

首样本结果：

- `cos_acc=0.9999874493614149`
- `cos_yaw_rate=0.9999900494945941`

结论：

- TensorRT 的 precision constraint 对这份图是有效的
- 真问题是：当前保护范围太小

### 6.6 有效解：只把 `language_model + nav_encoder + mlp_head` 三段浮点层钉成 FP32

实验 engine：

- `trajectory_mlp_e2e_v2_debug.lm_nav_mlp_fp32.bf16.trt`

方法：

- parse 后，对 layer 名中包含以下任意子串、且输出是浮点类型的 layer，统一设 `layer.precision = FLOAT`
  - `"/language_model/"`
  - `"/nav_encoder/"`
  - `"/mlp_head/"`
- build flag 使用：
  - `BF16`
  - `OBEY_PRECISION_CONSTRAINTS`

首样本结果：

- `cos_acc=0.9999873706894794`
- `cos_yaw_rate=0.9999824730654692`

10 样本结果：

- `passed=10/10`
- worst sample：
  - `cos_acc=0.999989`
  - `cos_yaw_rate=0.999968`

对应报告：

- engine：`/iag_ad_vepfs_volc/iag_ad_vepfs_volc/liangfenghe/trajectory_mlp_fp32/step_24800_reexport_merge_66a4f32_fix5_explicit_suffix/trajectory_mlp_e2e_v2_debug.lm_nav_mlp_fp32.bf16.trt`
- html：`/iag_ad_vepfs_volc/iag_ad_vepfs_volc/liangfenghe/trajectory_mlp_fp32/step_24800_reexport_merge_66a4f32_fix5_explicit_suffix/trajectory_mlp_e2e_v2_debug.lm_nav_mlp_fp32.bf16.alignment.html`

这是本轮最重要的可复现结论。

## 7. 我准备但还没正式落地的代码方案

我本来要做的正式化方案是：

### 7.1 导出端

在 `scripts/export_trajectory_mlp_onnx.py` 的 `precision_policy` metadata 里，把：

- 现有的 `trt_layer_name_patterns`

扩展为包含：

- 原有 norm/softmax pattern
- 额外的 BF16 子图 pattern：
  - `"/language_model/"`
  - `"/nav_encoder/"`
  - `"/mlp_head/"`

并把 metadata version 从 `1.1` 提到 `1.2`。

### 7.2 TRT 转换端

修改 `scripts/convert_onnx_to_trt_v2.py` 的 `_apply_fp32_layer_precision_from_onnx_metadata()`：

- 不只吃逐节点 `precision_hint`
- 还要读 `metadata_props["precision_policy"]` 里的 `trt_layer_name_patterns`
- 对匹配这些 pattern、且输出 dtype 为浮点的 TRT layer，也做 `layer.precision = FLOAT`

### 7.3 BF16 builder flag

对 BF16 build，优先使用：

- `OBEY_PRECISION_CONSTRAINTS`

如果 TRT 版本没有这个 flag，再退回：

- `PREFER_PRECISION_CONSTRAINTS`

### 7.4 TRT 对齐脚本

同样把 `scripts/trt_alignment_streaming_v2.py` 的 BF16 build 改成：

- 使用上面增强后的 metadata 消费逻辑
- BF16 时优先开 `OBEY_PRECISION_CONSTRAINTS`

## 8. 为什么这套方案是可信的

因为这不是凭感觉改的，而是有以下证据链：

1. 最初 ONNX 确实没 hint
2. 仅补 hint 后，BF16 仍然 0/10 失败
3. FP32 在同一脚本下是好的
4. debug 输出表明误差主源在 `plan_query_hidden`
5. 单个 op type 级别的小修小补基本无效
6. 一旦把更大的 `language_model + nav_encoder + mlp_head` 浮点子图钉成 FP32，10/10 通过

## 9. 建议下一个对话从哪里接着做

建议直接按这个顺序继续：

1. 不要再做新的定位实验，已有结论已经足够
2. 先把“第 7 节”的正式化代码改动真正写回远端
3. 对当前 ONNX 再跑一次正式 metadata 更新
4. 用脚本本身重建标准命名的 BF16 engine
5. 再用 `full_forward_dump.pb` 跑 10 样本确认
6. 如果要更稳，再扩到 50 或 100 样本

## 10. 本轮生成过的关键 BF16 engine/报告

失败类：

- `trajectory_mlp_e2e_v2_debug.precision_hint.bf16.trt`
- `trajectory_mlp_e2e_v2_debug.precision_hint.bf16.alignment.html`
- `trajectory_mlp_e2e_v2_debug.precision_hint_all_softmax_fp32.bf16.trt`
- `trajectory_mlp_e2e_v2_debug.rmsnorm_fullchain.bf16.trt`
- `trajectory_mlp_e2e_v2_debug.all_matmul_fp32.bf16.trt`
- `trajectory_mlp_e2e_v2_debug.pattern_fp32.bf16.trt`
- `trajectory_mlp_e2e_v2_debug.obey_only.bf16.trt`

成功类：

- `trajectory_mlp_e2e_v2_debug.lm_nav_mlp_fp32.bf16.trt`
- `trajectory_mlp_e2e_v2_debug.lm_nav_mlp_fp32.bf16.alignment.html`

## 11. 需要特别提醒的状态

### 11.1 当前远端代码不是完全干净的最终态

已经确认存在的远端改动：

- `scripts/export_trajectory_mlp_onnx.py`：部分改动已落地
- `scripts/onnx_alignment_streaming_v2.py`：此前已有别的改动，不是我本轮造成的
- `scripts/trt_alignment_streaming_v2.py`：我本轮做过改动，但还没有正式化成最终版本

### 11.2 当前 ONNX 头部已被多次实验性修改

如果下一个对话想把状态彻底整理干净，最稳妥的方法是：

1. 先把代码修好
2. 再重新导出一次 `trajectory_mlp_e2e_v2_debug.onnx`
3. 再重建 BF16 engine

但如果只想先继续验证，也可以直接在当前现有 ONNX 基础上工作。

## 12. 一句话结论

“ONNX 缺少 precision_hint”确实是问题的一部分，但不是全部。  
真正能让 BF16 TRT 对齐通过的策略，是在 BF16 build 时把 `language_model + nav_encoder + mlp_head` 三段浮点层整体钉回 FP32；这条策略已经在远端现有 dump 上跑到 `10/10` 通过。

## 13. 2026-05-15 新进展（本轮补充）

### 13.1 `fix6` 标准 streaming_v2 ONNX 的 metadata 状态

已确认远端源码中的 `export_combined_trajectory_model_streaming_v2()` 末尾现在确实有：

- `print(f"[export_streaming_v2] exported to {output_path}")`
- `_annotate_onnx_precision_policy(output_path, has_kinematic_rollout=True)`

但之前新导出的标准 ONNX：

- `/iag_ad_vepfs_volc/iag_ad_vepfs_volc/liangfenghe/trajectory_mlp_fp32/step_24800_reexport_fix6_precision_policy/trajectory_mlp_e2e_v2.onnx`

最初头部仍然是空的：

- `meta_keys=[]`
- `has_precision_policy=false`
- `hint_nodes=0`

随后直接对这份文件单独执行 `_annotate_onnx_precision_policy(...)`，可以立刻生效，结果变为：

- `meta_keys=['precision_policy']`
- `hint_nodes=396`
- `softmax_hint_nodes=28`
- `has_attention=false`

这说明：

- 注释函数本身是有效的
- 但“那次 fix6 标准导出”没有把注释结果保留到最终 ONNX 文件里
- 根因还没完全追到，但当前这份 fix6 文件现在已经被手动补成“带 precision policy 的标准 ONNX”

### 13.2 一个新的关键发现：`precision_hint` node attribute 会让 ORT 判图非法

对这份手动补完 metadata 的 fix6 ONNX 直接跑 ORT 时，出现：

- `InvalidGraph: Error Unrecognized attribute: precision_hint for operator Cast`

结论：

- 当前实现把 `precision_hint` / `precision_reason` 作为自定义 node attribute 写回标准 ONNX 节点
- 这会破坏 ORT 对该图的 schema 校验
- 因此“带 hint 的 ONNX”目前不能再直接作为 ORT 对齐基线使用
- 现阶段更合理的产物拆分是：
  - 一份干净的 ORT baseline ONNX（不带自定义 node attribute）
  - 一份供 TRT 转换使用的 precision-policy ONNX

### 13.3 当前 exporter / precision policy 默认会把哪些部分标成 FP32

从 `scripts/export_trajectory_mlp_onnx.py` 当前实现来看，默认 precision policy 包含：

1. 按 op type 直接要求 FP32：
- `Softmax`
- `LayerNormalization`
- `Resize`
- `CumSum`（仅 rollout 图）

2. 拓扑识别补充：
- Qwen3 文本 RMSNorm primitive-op 子图
- kinematic rollout 子图里的上游 `Mul/Add`、下游 `Sin/Cos`

3. model-level `precision_policy` 里的 TRT layer name pattern：
- `layernorm`
- `layer_norm`
- `rmsnorm`
- `rms_norm`
- `input_layernorm`
- `post_attention_layernorm`
- `q_norm`
- `k_norm`
- `softmax`

注意：

- 这些默认 pattern 里还不包含我后面实验性追加的三段大子图前缀：
  - `"/language_model/"`
  - `"/nav_encoder/"`
  - `"/mlp_head/"`
- 所以上述三段保护当前还属于“实验性 TRT 额外覆盖”，不是 exporter 默认行为

### 13.4 TensorRT MHA / FMHA fusion 实际状态

针对当前 fix6 标准 ONNX，直接用 TensorRT parser 检查网络层：

- `parse_ok=true`
- `num_layers=9576`
- `iattention_count=0`
- `attention_like_layers=[]`

另外对现有 BF16 engine 用 inspector 抽查：

- 没有发现 `MHA` / `FMHA` / `IAttention` 相关层名
- 只出现了普通输入名里的 `attention_mask`

因此当前结论是：

- 这份 `streaming_v2 trajectory_mlp_e2e_v2.onnx` 并没有走 ONNX `Attention -> TRT IAttention/FMHA` 这条路径
- 当前问题不属于“FMHA 里的 Softmax 是否保 FP32”那一类
- 更接近普通 primitive / fused layer 在 BF16 下的数值漂移问题

### 13.5 2026-05-15 本轮实际复核到的对齐结果

#### ONNX Runtime（沿用此前已验证的干净 ONNX 结果）

这轮没有重跑 ORT，因为手动补完 `precision_hint` 后的 fix6 ONNX 已不再能被 ORT 接受。沿用此前已经验证过的结果：

- ORT CUDA，TF32 关：`169/169` 通过
  - 报告：`/iag_ad_vepfs_volc/iag_ad_vepfs_volc/liangfenghe/reports/step24800_fix5_explicit_suffix_alignment_all_169_cuda_tf32_off.html`
- ORT CUDA，TF32 开：`168/169` 通过
  - 旧报告对应 TF32 漂移场景

#### TRT FP32（本轮重跑，基于 fix6 标准 ONNX）

本轮新结果：

- engine：`/iag_ad_vepfs_volc/iag_ad_vepfs_volc/liangfenghe/trajectory_mlp_fp32/step_24800_reexport_fix6_precision_policy/trajectory_mlp_e2e_v2.fp32.trt`
- report：`/iag_ad_vepfs_volc/iag_ad_vepfs_volc/liangfenghe/reports/step24800_fix6_precision_policy_trt_fp32_alignment_all_169.html`
- summary：`169/169` 通过

#### TRT BF16：`language_model + nav_encoder + mlp_head` 额外强制 FP32

构建方式：

- 先应用 metadata 里的逐节点 FP32 override：
  - `fp32_annotated=368`
  - `fp32_skipped=28`（Softmax，FMHA mode）
  - `fp32_layers_set=368`
- 再额外把以下三段前缀匹配到的浮点层统一设 `layer.precision=FLOAT`：
  - `"/language_model/"`
  - `"/nav_encoder/"`
  - `"/mlp_head/"`
- 额外设成 FP32 的层数：`2805`
- builder constraint flag：`OBEY_PRECISION_CONSTRAINTS`

结果：

- engine：`trajectory_mlp_e2e_v2.lm_nav_mlp_fp32.bf16.trt`
- report：`step24800_fix6_precision_policy_trt_bf16_lm_nav_mlp_fp32_alignment_all_169.html`
- summary：`76/169` 通过

说明：

- 10 样本小集合上曾经看起来可行
- 扩到 169 样本后明显不够

#### TRT BF16：所有浮点层都设 `layer.precision=FLOAT`

构建方式：

- 对所有“输出 dtype 为 FLOAT/HALF/BF16”的 TRT layer 统一设 `layer.precision=FLOAT`
- 共设置：`4064` 层
- constraint flag：`OBEY_PRECISION_CONSTRAINTS`

结果：

- engine：`trajectory_mlp_e2e_v2.all_float_fp32.bf16.trt`
- report：`step24800_fix6_precision_policy_trt_bf16_all_float_fp32_alignment_all_169.html`
- summary：`77/169` 通过

这说明：

- 仅设置 `layer.precision=FLOAT` 还不够
- TRT 仍然可能在层间把张量保成 BF16，误差继续累积

#### TRT BF16：所有浮点层同时设 `layer.precision=FLOAT` + `set_output_type(FLOAT)`

构建方式：

- 对所有浮点层：
  - `layer.precision = FLOAT`
  - `layer.set_output_type(..., FLOAT)`
- 共设置：
  - `all_float_layers_set=4064`
  - `all_float_outputs_set=4064`
- constraint flag：`OBEY_PRECISION_CONSTRAINTS`

结果：

- engine：`trajectory_mlp_e2e_v2.all_float_io_fp32.bf16.trt`
- report：`step24800_fix6_precision_policy_trt_bf16_all_float_io_fp32_alignment_all_169.html`
- summary：`77/169` 通过

说明：

- 甚至把所有浮点层的输出类型也钉成 FP32，169 样本仍然没有恢复到全通过
- 当前 BF16 偏差不是简单的“再多加几个 layer pattern”就能解决的问题

### 13.6 当前阶段结论

本轮已经把边界收得比较清楚：

1. 当前 `precision_hint` 写法会破坏 ORT，因此 ORT baseline ONNX 与 TRT precision-policy ONNX 需要拆开
2. 当前图里没有 `IAttention` / `MHA` / `FMHA` 路径，Softmax-FMHA 不是主问题
3. TRT FP32 已经在 fix6 标准 ONNX 上重新验证为 `169/169`
4. TRT BF16 到目前仍未完成 169 样本全通过：
   - `lm+nav+mlp` 保护：`76/169`
   - `all_float layer.precision=FP32`：`77/169`
   - `all_float precision + output_type = FP32`：`77/169`

因此，BF16 这条线当前还不能宣称“已经对齐完成”。更像是 TensorRT 在这条图上的底层 dtype propagation / kernel 选择行为，已经超出简单 metadata / pattern override 的可控范围，下一步应该转向更底层的 engine inspector / layer-wise precision dump / 实际 tensor dtype 传播排查。
