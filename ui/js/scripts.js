// @ts-nocheck

// 创建toasts容器
function createToastContainer() {
    // 检查是否已经存在toast容器
    let toastContainer = document.getElementById('toast-container');
    if (!toastContainer) {
        toastContainer = document.createElement('div');
        toastContainer.id = 'toast-container';
        toastContainer.className = 'toast-container position-fixed bottom-0 end-0 p-3';
        toastContainer.style.zIndex = '1050';
        document.body.appendChild(toastContainer);
    }
    return toastContainer;
}

// 显示toast消息
function showToast(message, type = 'success') {
    const toastContainer = createToastContainer();
    
    // 创建toast元素
    const toastEl = document.createElement('div');
    toastEl.className = 'toast';
    toastEl.setAttribute('role', 'alert');
    toastEl.setAttribute('aria-live', 'assertive');
    toastEl.setAttribute('aria-atomic', 'true');
    
    const bgClass = type === 'success' ? 'bg-success text-white' : 
                   type === 'danger' ? 'bg-danger text-white' : 
                   type === 'warning' ? 'bg-warning text-dark' : 'bg-info text-white';
    
    const icon = type === 'success' ? '✓' : 
                type === 'danger' ? '✗' : 
                type === 'warning' ? '⚠' : 'ℹ';
    
    toastEl.innerHTML = `
        <div class="toast-body ${bgClass} d-flex align-items-center">
            <span class="me-2">${icon}</span>
            <div class="flex-grow-1">${message}</div>
            <button type="button" class="btn-close btn-close-white ms-2" data-bs-dismiss="toast" aria-label="Close"></button>
        </div>
    `;
    
    toastContainer.appendChild(toastEl);
    
    // 初始化并显示toast
    const toast = new bootstrap.Toast(toastEl, {
        delay: 3000,
        autohide: true
    });
    
    // 监听hidden事件，在toast完全隐藏后移除元素
    toastEl.addEventListener('hidden.bs.toast', function () {
        toastEl.remove();
    });
    
    // 显示toast
    toast.show();
}

// 显示确认对话框
function showConfirm(message, callback) {
    // 获取确认对话框元素
    const confirmModal = document.getElementById('confirmModal');
    const confirmModalBody = document.getElementById('confirmModalBody');
    
    // 设置消息内容
    confirmModalBody.textContent = message;
    
    // 创建一个新的Bootstrap模态框实例
    const modal = new bootstrap.Modal(confirmModal);
    
    // 定义事件处理函数
    function handleConfirm() {
        modal.hide();
        callback(true);
    }
    
    function handleCancel() {
        modal.hide();
        callback(false);
    }
    
    // 获取按钮
    const confirmOkBtn = document.getElementById('confirmOkBtn');
    const cancelBtns = confirmModal.querySelectorAll('[data-bs-dismiss="modal"]');
    
    // 添加事件监听器
    confirmOkBtn.addEventListener('click', handleConfirm);
    
    // 为所有取消按钮添加事件监听器
    cancelBtns.forEach(btn => {
        btn.addEventListener('click', handleCancel);
    });
    
    // 监听模态框隐藏事件以清理监听器
    function onHidden() {
        confirmOkBtn.removeEventListener('click', handleConfirm);
        cancelBtns.forEach(btn => {
            btn.removeEventListener('click', handleCancel);
        });
        confirmModal.removeEventListener('hidden.bs.modal', onHidden);
    }
    
    confirmModal.addEventListener('hidden.bs.modal', onHidden);
    
    // 显示模态框
    modal.show();
}