# StudySearch · 学习资料检索器

输入一个问题，在本地 PDF 中找到相关原文，并定位到文件和页码。

这是一个用于学习信息检索的 Python 项目：主程序集中在 `app.py`，包含 PDF 解析、中文分词、TF-IDF 索引、关键词基线、结果排序和 Streamlit 界面。它不调用大模型，不生成答案，不需要 API 密钥。

## 快速开始

建议使用 Python 3.11 或 3.12。在项目目录打开终端：

```powershell
python -m venv .venv
.venv\Scripts\python -m pip install -r requirements.txt
.venv\Scripts\python -m streamlit run app.py
```

浏览器打开终端显示的本地地址，通常是 http://127.0.0.1:8501 。Windows 也可以双击 `启动项目.bat`，首次会创建环境并下载依赖。

macOS / Linux：

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
.venv/bin/python -m streamlit run app.py
```

首次安装依赖需要网络。安装后，使用内置示例与本地 PDF 不需要网络。若安装失败，保留终端报错；不要反复双击关闭窗口。

## 怎么演示

1. 左侧选择“内置示例”。随项目附带一份自编的 16 页数学与机器学习笔记。
2. 输入“什么是矩阵的秩”，观察相关段落、关键词高亮和物理页码。
3. 勾选“查看原始页面与上下文”，直接核对原始 PDF 页面。
4. 切换为“关键词覆盖率”，比较结果排序。
5. 输入“背熟了练习题换一套题却不会做怎么办”，观察词语匹配对同义改写的局限。
6. 上传自己的课程 PDF，并选择检索范围；可下载 JSON 结果作为实验记录。

## 功能与边界

- 多 PDF 检索、同内容去重、按文件筛选、原页预览、结果导出。
- 每份最多 30 MB / 500 页，每批最多 10 份 / 100 MB。
- 优先按句末切块，最长约 450 字符，重叠约 70 字符，段落不跨页。
- 页码从 PDF 的第一张物理页面起算，可能不等于教材印刷页码。
- 支持文字型 PDF。空白页、扫描页会提示；不含 OCR，不支持密码保护文档。
- 复杂双栏、公式、表格的提取顺序可能有误，原页预览用于核验。
- 不具备语义理解、跨段落推理或事实验证能力。相关性分数不是正确率。
- 无共同词语时不返回结果；有词语重合也可能返回不相关内容。本版没有经过验证的“拒答”阈值。
- 同页的重叠段落可能同时出现；大文件可能建索引较慢，大小限制不代表性能保证。
- 本地启动时 PDF 不发送给外部模型服务，也不主动保存到项目目录；索引和文件保存在当前会话内存。若部署到服务器，上传资料会到达该服务器，需要另行设计访问控制。

## 原理

```text
PDF → 按页提取文字 → 页内分块 → jieba 分词 → TF-IDF 稀疏矩阵
问题 → 相同分词与词表 → 查询向量 → 余弦相似度 → 原文、出处、页码
```

两种方法使用相同分词和停用词规则，尽量只比较排序方法：

- **关键词基线**：查询中被段落覆盖的不同词数 / 查询的不同词数。并列分数按资料原始顺序排序。
- **TF-IDF**：词频采用 `1 + log(tf)`，逆文档频率采用 scikit-learn 默认平滑方式 `log((1+n)/(1+df))+1`；L2 归一化后，用内积计算余弦相似度。这里的“文档”单位是切分后的段落。

项目没有训练神经网络。建立 TF-IDF 词表和统计词权重属于建立检索索引，不能描述成训练了大语言模型。

## 运行评估与测试

```powershell
.venv\Scripts\python -m unittest discover -s tests -v
.venv\Scripts\python evaluate.py
```

`evaluation/questions.csv` 固定了 20 个有答案问题和 4 个资料外问题。相关页码由编写示例的人预先指定，不是独立评审标注。两种算法共用语料、查询、分词器和前 5 条返回限制。

- Hit@1 / Hit@5：20 个有答案问题中，前 1 / 5 个段落是否至少有一条来自相关页。
- MRR@5：第一个正确页结果排名的倒数的均值；未命中记 0。
- 资料外返回率：4 个无答案问题中返回非空结果的比例。这反映误导风险，不是事实错误率。
- 查询耗时：索引建立后先预热，每题运行 20 次取中位数，再汇总；不包括 PDF 解析、索引和界面渲染。

真实运行结果保存在 `evaluation/results.csv` 和 `evaluation/summary.json`，包括环境信息。**该数据集很小且为自编示例，不能据此宣称适用于所有教材，也不能保证 TF-IDF 总比关键词基线好。** 计时会随电脑和系统负载变化。

## 文件结构

```text
app.py                    主程序与检索核心
build_sample.py           从自编文本重新生成 PDF
evaluate.py               可复现对比实验
requirements.txt          依赖范围
requirements-lock.txt     本次验证的直接依赖版本
samples/lessons.json       自编示例原文
samples/study_notes.pdf    16 页示例资料
evaluation/questions.csv  预设评估题和相关页
evaluation/results.csv    逐题实测结果
evaluation/summary.json   汇总指标与环境信息
tests/test_app.py          核心行为测试
docs/答辩与发布指南.md     演示、答辩准备和发布步骤
```

## 进一步完善

先用一份有权使用的真实课程资料，独立准备更多问题、记录失败案例，再考虑同义词扩展、OCR、语义向量检索或重排序。新增算法应保留同一基线、增加独立测试集，而不是只展示有利的问题。

## 来源与许可

示例笔记是为本项目自编的演示材料，不复制教材。代码和文档是在 AI 辅助下形成的初始版本；使用者应理解、验证并如实说明自己的修改与贡献。尚未指定项目作者身份或项目开源许可证；公开 GitHub 仓库不等于授予开源许可。正式选择许可证前应核对依赖条款，尤其是 PyMuPDF 的 AGPL / 商业许可选项。

参考官方文档：

- [Streamlit 文件上传](https://docs.streamlit.io/develop/api-reference/widgets/st.file_uploader)
- [Streamlit 下载按钮](https://docs.streamlit.io/develop/api-reference/widgets/st.download_button)
- [scikit-learn TF-IDF](https://scikit-learn.org/stable/modules/generated/sklearn.feature_extraction.text.TfidfVectorizer.html)
- [PyMuPDF 文本提取](https://pymupdf.readthedocs.io/en/latest/recipes-text.html)
- [PyMuPDF 许可](https://pymupdf.readthedocs.io/en/latest/about.html#license-and-copyright)

请勿上传私人课程材料、成绩单、个人信息或密钥；示例文件已可满足公开演示需要。
