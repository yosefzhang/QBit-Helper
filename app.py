from flask import Flask, render_template, request, jsonify, redirect, url_for
import os
import yaml
from qbit_helper import QBitHelperBasic, DashboardInfo

# 配置Flask应用，指定模板和静态文件目录
app = Flask(__name__, 
            template_folder=os.path.join(os.getcwd(), 'ui', 'templates'),
            static_folder=os.path.join(os.getcwd(), 'ui'))

# 静态资源默认缓存时间（秒），减小重复请求
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 60 * 60 * 24 * 30  # 30天

# 配置文件路径
CONFIG_FILE = os.path.join('data', 'config.yaml')

# 初始化QBitHelperBasic
qbhper = QBitHelperBasic(CONFIG_FILE)


# 前端页面路由
@app.route('/')
def index():
    """重定向到仪表盘页面"""
    return redirect('/dashboard')


@app.route('/dashboard')
def dashboard():
    """返回仪表盘页面"""
    return render_template('dashboard.html')


@app.route('/tasks')
def tasks():
    """返回任务页面"""
    return render_template('tasks.html')


@app.route('/settings')
def settings():
    """返回设置页面"""
    return render_template('settings.html')


# API路由定义
@app.route('/api/dashboard/info', methods=['GET'])
def get_dashboard_info():
    """获取仪表板信息"""
    try:
        # 使用QBitHelperBasic实例获取实际的仪表板信息
        info = qbhper.get_dashboard_info()
        return jsonify({
            'success': True,
            'data': {
                'total_torrents': info.total_torrents,
                'total_trackers': info.total_trackers,
                'non_working_trackers': info.non_working_trackers,
                'category_counts': info.category_counts,
                'tag_counts': info.tag_counts
            }
        })
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# 用户配置相关的API接口
@app.route('/api/config/reload_config', methods=['POST'])
def reload_config():
    """重载配置"""
    try:
        # 重新初始化QBitHelperBasic实例以加载最新配置
        global qbhper
        qbhper = QBitHelperBasic(CONFIG_FILE)
        return jsonify({'success': True, 'message': '配置重载成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/config/save_user_config', methods=['POST'])
def save_user_config():
    """保存用户配置"""
    try:
        config_data = request.json
        qbhper.save_user_config(config_data)
        return jsonify({'success': True, 'message': '用户配置保存成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/config/get_user_config', methods=['GET'])
def get_user_config():
    """获取用户配置"""
    try:
        config = qbhper.get_user_config()
        return jsonify({'success': True, 'data': config})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/config/save_user_rules', methods=['POST'])
def save_user_rules():
    """保存用户规则"""
    try:
        rules_data = request.json
        # 直接使用规则列表数据
        qbhper.save_user_rules(rules_data)
        return jsonify({'success': True, 'message': '用户规则保存成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/config/get_user_rules', methods=['GET'])
def get_user_rules():
    """获取用户规则"""
    try:
        rules = qbhper.get_user_rules()
        # 直接返回规则列表
        return jsonify({'success': True, 'data': rules})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# 用户任务相关的API接口
@app.route('/api/config/get_user_tasks', methods=['GET'])
def get_user_tasks():
    """获取用户任务"""
    try:
        tasks = qbhper.get_user_tasks()
        return jsonify({'success': True, 'data': tasks})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/config/save_user_tasks', methods=['POST'])
def save_user_tasks():
    """保存用户任务"""
    try:
        tasks_data = request.json
        qbhper.save_user_tasks(tasks_data)
        return jsonify({'success': True, 'message': '用户任务保存成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# 任务执行相关的API接口
@app.route('/api/task/execute_manual_task', methods=['POST'])
def execute_manual_task():
    """执行手动任务"""
    try:
        # 获取请求数据
        data = request.json
        task_index = data.get('task_index')
        
        # 获取用户任务
        user_tasks = qbhper.get_user_tasks()
        tasks = user_tasks.get('tasks', [])
        
        # 验证任务索引
        if task_index < 0 or task_index >= len(tasks):
            return jsonify({'success': False, 'message': '任务索引无效'}), 400
        
        # 获取任务信息
        task = tasks[task_index]
        task_name = task.get('task_name', '未命名任务')
        rules_string = task.get('rules', '')
        
        # 解析规则字符串
        if rules_string:
            rule_names = rules_string.split('|')
            # 获取所有用户规则
            all_rules = qbhper.get_user_rules()
            # 筛选出匹配的规则
            matched_rules = [rule for rule in all_rules if rule.get('rule_name') in rule_names]
        else:
            matched_rules = []
        
        qbhper.logger.info(f'执行手动任务："{task_name}"，规则：{[rule.get("rule_name") for rule in matched_rules]}')
        results = qbhper.opt_all_torrent(matched_rules)
        
        # 返回执行结果
        return jsonify({
            'success': True,
            'message': f'手动任务 "{task_name}" 执行完成',
            'data': results
        })
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'执行手动任务时发生错误: {str(e)}'}), 500


@app.route('/api/task/toggle_auto_task', methods=['POST'])
def toggle_auto_task():
    """启用/禁用自动任务"""
    try:
        # 获取请求数据
        data = request.json
        task_index = data.get('task_index')
        enable = data.get('enable', True)
        
        # 获取用户任务
        user_tasks = qbhper.get_user_tasks()
        tasks = user_tasks.get('tasks', [])
        
        # 验证任务索引
        if task_index < 0 or task_index >= len(tasks):
            return jsonify({'success': False, 'message': '任务索引无效'}), 400
        
        # 获取任务信息
        task = tasks[task_index]
        task_name = task.get('task_name', '未命名任务')
        
        if enable:
            # 启用自动任务，将任务添加到调度器
            qbhper.add_auto_task_to_scheduler(task_index, task)
            return jsonify({
                'success': True, 
                'message': f'自动任务 "{task_name}" 已启用'
            })
        else:
            # 禁用自动任务，从调度器中移除任务
            qbhper.remove_auto_task_from_scheduler(task_index)
            return jsonify({
                'success': True, 
                'message': f'自动任务 "{task_name}" 已禁用'
            })
    except Exception as e:
        return jsonify({'success': False, 'message': f'切换自动任务状态时发生错误: {str(e)}'}), 500


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)