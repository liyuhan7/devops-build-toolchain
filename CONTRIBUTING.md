# Contributing Guide

本文件用于约定项目日常协作方式，包括分支、Issue、Commit、Pull Request 和代码审查。

## 1. 基本原则

- 不直接在 `main` 分支开发。
- 一个分支尽量只处理一个明确任务。
- 一个 Pull Request 尽量只包含一个主题。
- 重要讨论尽量留在 Issue 或 PR 中，避免只存在聊天记录。
- 合并前保证代码或文档处于可用状态。

## 2. Branch

主分支：

```text
main
```

所有功能开发从最新的 `main` 创建新分支。

开始工作前：

```bash
git checkout main
git pull origin main
git checkout -b feature/xxx
```

推荐分支命名：

```text
feature/<description>
fix/<description>
docs/<description>
refactor/<description>
test/<description>
```

例如：

```text
feature/job-schema
feature/build-tracer
fix/artifact-uri
docs/update-readme
refactor/error-handler
```

避免使用：

```text
test
new
dev
mybranch
final
```

这类无法体现工作内容的名称。

## 3. Issue

对于需要多人协作、需要讨论或工作量较大的任务，先创建 Issue。

Issue 建议至少说明：

```md
## Description

要解决什么问题。

## Tasks

- [ ] 子任务 1
- [ ] 子任务 2

## Acceptance

怎样算完成。
```

开发分支和 PR 应关联对应 Issue。

例如：

```text
Closes #12
```

或：

```text
Related to #12
```

小规模修改，例如错别字、简单文档调整，可以不单独创建 Issue。

## 4. Commit

Commit 应保持小而清晰。

推荐格式：

```text
<type>: <description>
```

常用 type：

```text
feat      新功能
fix       Bug 修复
docs      文档修改
refactor  重构
test      测试
chore     工程配置或其他维护
```

例如：

```text
feat: add job schema
fix: handle missing baseline
docs: update repository structure
test: add invalid request cases
refactor: simplify artifact parser
```

避免：

```text
update
修改一下
fix
test
final
final2
```

一个 Commit 尽量只表达一个逻辑修改。

## 5. Push

首次推送新分支：

```bash
git push -u origin feature/xxx
```

之后：

```bash
git push
```

提交前建议确认：

```bash
git status
git diff
```

避免误提交：

- IDE 临时文件
- 日志
- 本地配置
- 密钥
- 大型生成文件

这些内容应该加入 `.gitignore`。

## 6. Pull Request

功能完成后提交 Pull Request 到 `main`。

PR 标题应清楚说明修改内容，例如：

```text
Add common job schema
Implement build tracer
Fix artifact URI validation
Update collaboration guide
```

PR 描述建议包含：

```md
## What

本次修改了什么。

## Why

为什么需要修改。

## Changes

- 修改内容 1
- 修改内容 2

## Validation

如何验证本次修改。

## Related

Closes #xx
```

如果有尚未完成或已知问题，也应在 PR 中说明。

## 7. Code Review

原则上 PR 由至少一名其他成员 Review 后再合并。

Reviewer 主要检查：

- 修改是否符合任务目标
- 是否存在明显错误
- 是否影响其他已有功能
- 是否遗漏必要文件
- 文档是否需要同步修改

如果需要修改，Reviewer 在 PR 中留言。

作者修改后再次 Push：

```bash
git add .
git commit -m "fix: address review comments"
git push
```

PR 会自动更新，不需要重新创建。

## 8. Merge

PR Review 通过后再合并到 `main`。

建议使用：

```text
Squash and merge
```

如果一个分支存在大量零碎 Commit，可以在合并时整理为一个清晰的 Commit。

合并后删除远程分支。

本地同步：

```bash
git checkout main
git pull origin main
git branch -d feature/xxx
```

## 9. 保持分支同步

如果开发时间较长，定期同步 `main`：

```bash
git checkout main
git pull origin main

git checkout feature/xxx
git merge main
```

如果发生冲突：

```bash
git status
```

手动解决冲突后：

```bash
git add .
git commit
git push
```

不要在不了解冲突内容的情况下直接覆盖别人的修改。

## 10. Rebase

Rebase 适合在提交 PR 前，将个人开发分支更新到最新的 `main`，并保持提交历史清晰。

先确认工作区没有未提交修改：

```bash
git status
```

获取最新远程分支并执行 Rebase：

```bash
git fetch origin
git checkout feature/xxx
git rebase origin/main
```

如果发生冲突，Git 会暂停 Rebase。查看冲突文件：

```bash
git status
```

手动处理冲突后继续：

```bash
git add <resolved-file>
git rebase --continue
```

如果当前 Rebase 不应继续，可以恢复到开始前的状态：

```bash
git rebase --abort
```

如果分支此前已经推送到远程，Rebase 会改变 Commit 历史。确认该分支只有自己使用后，采用：

```bash
git push --force-with-lease
```

不要使用：

```bash
git push --force
```

Rebase 约定：

- 不 Rebase `main`。
- 不 Rebase 其他成员正在共同使用的分支。
- 已经有其他成员基于该分支开发时，先沟通再改写历史。
- `--force-with-lease` 仅用于自己拥有且已经 Rebase 的开发分支。
- 不确定冲突应如何处理时，先执行 `git rebase --abort` 并与相关成员确认。

## 11. 常用工作流程

完整流程：

```text
Issue
  ↓
更新 main
  ↓
创建 Branch
  ↓
开发
  ↓
Commit
  ↓
Push
  ↓
Pull Request
  ↓
Review
  ↓
修改
  ↓
Merge
  ↓
删除 Branch
```

对应命令：

```bash
git checkout main
git pull origin main

git checkout -b feature/example

# 修改代码

git add .
git commit -m "feat: add example"

git push -u origin feature/example
```

之后在 GitHub 创建 PR，Review 通过后合并。

## 12. 协作约定

- 不直接向 `main` push。
- 不强制覆盖远程分支，除非团队成员已经确认。
- 不提交密码、Token、API Key 等敏感信息。
- 不随意修改其他成员正在开发的文件。
- 发现冲突及时沟通，不自行覆盖。
- 开始较大任务前先确认是否已有其他人在处理。
- 合并后及时同步本地 `main`。
