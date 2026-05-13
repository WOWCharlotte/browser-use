---
name: aone-ci-generate
description: 生成符合Aone CI规范的流水线配置文件。触发场景：按需查询。输出.gitlab-ci.yml或.aone.yml。
---

# Aone CI配置生成

## 流水线结构

```yaml
stages:
  - build
  - test
  - deploy
```

## Job配置

### Build Job
```yaml
build:
  stage: build
  script:
    - uv sync
    - uv run pyright
```

### Test Job
```yaml
test:
  stage: test
  script:
    - uv run pytest -vxs tests/ci
  coverage: '/TOTAL.*\s+(\d+%)$/'
```

### Deploy Job
```yaml
deploy:
  stage: deploy
  script:
    - echo "Deploy"
  only:
    - main
```

## 质量门禁

- [ ] 测试阶段（禁止tests=0）
- [ ] 覆盖率检查 >= 80%
- [ ] 类型检查通过
- [ ] 格式化检查通过

## 输出文件
`.aone.yml` 或 `.gitlab-ci.yml`

## 质量门禁脚本

阶段完成后，可使用脚本验证产出物：

```bash
python scripts/check_quality_gate.py <output-dir>
```

**检查项**:
- 目录下存在 .yaml 或 .yml CI 配置文件

详细配置模板见 [references/ci-template.md](references/ci-template.md)
