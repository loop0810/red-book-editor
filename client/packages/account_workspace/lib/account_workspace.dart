import 'package:flutter/material.dart';

class AccountWorkspacePage extends StatefulWidget {
  const AccountWorkspacePage({super.key});

  @override
  State<AccountWorkspacePage> createState() => _AccountWorkspacePageState();
}

class _AccountWorkspacePageState extends State<AccountWorkspacePage> {
  final _positioningController = TextEditingController(
    text: '记录备孕、孕检到育儿全程的新手爸妈日常',
  );
  final _toneController = TextEditingController(text: '自然、具体、像朋友聊天');
  int _babyMonth = 19;
  final _columns = <String>['科普', '经验', '软文'];

  @override
  void dispose() {
    _positioningController.dispose();
    _toneController.dispose();
    super.dispose();
  }

  @override
  Widget build(BuildContext context) {
    return Scaffold(
      appBar: AppBar(title: const Text('账号工作台')),
      body: ListView(
        padding: const EdgeInsets.all(20),
        children: [
          TextField(
            controller: _positioningController,
            decoration: const InputDecoration(labelText: '账号定位'),
          ),
          const SizedBox(height: 12),
          TextField(
            controller: _toneController,
            decoration: const InputDecoration(labelText: '表达风格'),
          ),
          const SizedBox(height: 16),
          Text('当前宝宝：$_babyMonth 个月'),
          Slider(
            value: _babyMonth.toDouble(),
            min: 0,
            max: 24,
            divisions: 24,
            onChanged: (value) => setState(() => _babyMonth = value.round()),
          ),
          const SizedBox(height: 12),
          Text('内容栏目', style: Theme.of(context).textTheme.titleMedium),
          ..._columns.map(
            (column) => CheckboxListTile(
              value: true,
              onChanged: (_) {},
              title: Text(column),
            ),
          ),
          FilledButton(
            onPressed: () => Navigator.of(context).pop(),
            child: const Text('保存账号配置'),
          ),
        ],
      ),
    );
  }
}
