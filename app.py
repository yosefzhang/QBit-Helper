from flask import Flask, render_template, request, jsonify, redirect, url_for
import os
import yaml
from qbit_helper import QBitHelperBasic, DashboardInfo, APP_VERSION

# 配置Flask应用，指定模板和静态文件目录
app = Flask(__name__, 
            template_folder=os.path.join(os.getcwd(), 'ui', 'templates'),
            static_folder=os.path.join(os.getcwd(), 'ui'))

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
    return render_template('dashboard.html', app_version=APP_VERSION)


@app.route('/tasks')
def tasks():
    """返回任务页面"""
    return render_template('tasks.html', app_version=APP_VERSION)


@app.route('/rules')
def rules():
    """返回规则页面"""
    return render_template('rules.html', app_version=APP_VERSION)


@app.route('/settings')
def settings():
    """返回设置页面"""
    return render_template('settings.html', app_version=APP_VERSION)


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
                'tag_counts': info.tag_counts,
                'non_working_trackers_detail': info.non_working_trackers_detail
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
        qbhper.save_user_rules(rules_data)
        return jsonify({'success': True, 'message': '用户规则保存成功'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


@app.route('/api/task/get_task_results', methods=['GET'])
def get_task_results():
    """获取任务执行结果日志"""
    try:
        log_file_path = os.path.join('data', 'task_results.log')
        if os.path.exists(log_file_path):
            with open(log_file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            return jsonify({'success': True, 'data': content})
        else:
            return jsonify({'success': True, 'data': ''})
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
        
        # 调用qbit_helper中的方法执行手动任务
        result = qbhper.execute_manual_task(task_index)
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'success': False, 'message': f'执行手动任务时发生错误: {str(e)}'}), 500


@app.route('/api/config/test_webhooks', methods=['POST'])
def test_webhooks():
    """测试webhook配置"""
    try:
        result = qbhper.test_webhooks()
        return jsonify({'success': True, 'data': result})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500


# 用于Gunicorn部署的入口点
# 当使用Gunicorn运行时，不会执行以下代码
# Gunicorn会直接导入app对象: gunicorn --bind 0.0.0.0:8080 --workers 4 app:app

if __name__ == '__main__':
    # 仅在直接运行此脚本时执行（不推荐用于生产环境）
    app.run(debug=False, host='0.0.0.0', port=8080)