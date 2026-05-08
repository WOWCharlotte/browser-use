# CI配置模板

## 完整配置示例

```yaml
name: browser-use-ci
variables:
  PYTHON_VERSION: "3.11"

stages:
  - build
  - test
  - deploy

build:
  stage: build
  image: python:3.11
  before_script:
    - pip install uv
  script:
    - uv sync
    - uv run pyright
  artifacts:
    paths:
      - .venv/
    expire_in: 1 day

test:
  stage: test
  image: python:3.11
  script:
    - uv sync
    - uv run pytest -vxs tests/ci --cov=browser_use --cov-report=term-missing --cov-fail-under=80
  coverage: '/TOTAL.*\s+(\d+%)$/'
  dependencies:
    - build

deploy:
  stage: deploy
  script:
    - echo "Deploy to production"
  only:
    - main
  when: manual
```

## 环境变量配置

| 变量 | 说明 | 必需 |
|------|------|------|
| PYTHON_VERSION | Python版本 | Yes |
| COVERAGE_THRESHOLD | 覆盖率阈值 | No |
