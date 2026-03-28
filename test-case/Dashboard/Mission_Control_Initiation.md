## [P1] 验证合法IP和RECON工具启动任务成功
[测试类型] 功能
[前置条件] 进入仪表盘(Dashboard)
[测试步骤] 1. 在目标节点输入框输入"192.168.1.1"。2. 点击"RECON"工具按钮。3. 点击"START MISSION"按钮
[预期结果] 1. 输入框显示内容。2. RECON按钮被选中。3. 页面立即跳转到 "/task/{task_id}" 详情页

## [P1] 验证合法域名和WEB工具启动任务成功
[测试类型] 功能
[前置条件] 进入仪表盘(Dashboard)
[测试步骤] 1. 在目标节点输入框输入"example.local"。2. 点击"WEB"工具按钮。3. 点击"START MISSION"按钮
[预期结果] 1. 输入框显示内容。2. WEB按钮被选中。3. 任务启动成功并跳转到详情页

## [P3][反向] 验证目标节点为空时点击启动报错
[测试类型] 功能
[前置条件] 进入仪表盘(Dashboard),目标输入框为空
[测试步骤] 1. 点击"DB"工具按钮。2. 保持输入框为空,点击"START MISSION"按钮
[预期结果] 1. 输入边框显示红色高亮提示目标缺失。2. 任务未启动,未跳转

## [P4] 验证极端长域名输入稳定性
[测试类型] 稳定性
[前置条件] 进入仪表盘(Dashboard)
[测试步骤] 1. 输入一个长达255字符的测试域名 "long-subdomain-target-node-for-stress-testing-secuscan-interface-robustness-overflow-check-example-dns-resolution-node-full-path-target-string.com"。2. 选择任意工具启动并点击START MISSION。
[预期结果] 1. 系统能正常处理长字符串而不引发UI崩溃。2. 任务能够成功创建或返回合法的校验失败提示。

## [P2] 验证不同工具按钮的切换状态
[测试类型] 易用性
[前置条件] 进入仪表盘(Dashboard)
[测试步骤] 1. 依次点击"RECON"、"WEB"、"DB"、"BROWSER"并观察每个按钮的选中状态
[预期结果] 1. 每次点击后,仅新选中的按钮呈现高亮状态,旧的选中状态取消
