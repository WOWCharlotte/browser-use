# 需求树形图模板

## 说明

xmind.md 是需求分析阶段的第一个产出物，用于以树形图形式梳理业务需求的整体结构。

## 使用方式

1. 需求分析开始时，首先阅读用户需求描述
2. 识别核心概念、功能模块、用户角色
3. 生成 Mermaid Tree Diagram 格式树形图
4. 在需求评审阶段作为讨论的视觉辅助

## Mermaid Tree Diagram 语法

```mermaid
tree
root[根节点]
  branch1[分支1]
    leaf1[叶子1]
    leaf2[叶子2]
  branch2[分支2]
    leaf3[叶子3]
```

## 模板

```markdown
# {需求名称} - 树形图

## 概述
[一句话描述需求的核心价值]

## 树形图

```mermaid
tree
root[需求名称]
  core[核心模块]
    feature1[功能点1]
      input1[输入]
      output1[输出]
    feature2[功能点2]
  user[用户角色]
    role1[角色1]
      permission[权限]
      scenario[触达场景]
    role2[角色2]
  flow[业务流程]
    step1[步骤1]
    step2[步骤2]
    step3[步骤3]
  external[外部依赖]
    depA[依赖服务A]
    depB[依赖服务B]
  constraint[约束条件]
    perf[性能要求]
    security[安全要求]
```

## 核心概念解释

| 概念 | 定义 | 备注 |
|------|------|------|
|      |      |      |

## 待确认问题

| # | 问题描述 | 优先级 | 建议方案 |
|---|----------|--------|----------|
| 1 |          |        |          |
```

## 示例

```markdown
# 用户认证系统 - 树形图

## 概述
支持多种登录方式的用户认证系统，包括账号密码、手机验证码、第三方OAuth

## 树形图

```mermaid
tree
root[用户认证系统]
  login[登录方式]
    pwd[账号密码]
      username[用户名/邮箱]
      password[密码]
      remember[记住登录]
    sms[手机验证码]
      phone[手机号]
      code[验证码]
      countdown[倒计时]
    oauth[第三方OAuth]
      github[GitHub]
      google[Google]
      wecom[企业微信]
  user_mgmt[用户管理]
    register[注册]
      fill[信息填写]
      verify[验证]
    profile[个人信息]
      changepwd[修改密码]
      bindphone[绑定手机]
   注销[注销账号]
  security[安全机制]
    limit[登录限制]
      failcount[失败次数]
      locktime[锁定时间]
    detect[异常检测]
     异地[异地登录]
      fingerprint[设备指纹]
  flow[业务流程]
    login_flow[登录流程]
    register_flow[注册流程]
    resetpwd_flow[找回密码]
```

## 核心概念解释

| 概念 | 定义 | 备注 |
|------|------|------|
| OAuth | 开放授权协议 | 允许第三方应用访问用户在其他服务上的资源 |
| 设备指纹 | 设备的唯一标识 | 用于异常检测 |

## 待确认问题

| # | 问题描述 | 优先级 | 建议方案 |
|---|----------|--------|----------|
| 1 | 是否需要支持双因素认证？ | 高 | 第一阶段先不支持 |
| 2 | 登录会话过期时间？ | 中 | 建议 7 天 |
```
