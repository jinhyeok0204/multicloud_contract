// Flash 메시지 자동으로 사라지게 하기
setTimeout(function() {
    let alert = document.querySelector('.alert');
    if (alert) {
        alert.style.display = 'none';
    }
}, 3000);
