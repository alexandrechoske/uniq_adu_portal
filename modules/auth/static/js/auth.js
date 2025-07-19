document.addEventListener('DOMContentLoaded', function() {
    console.log('Página carregada, iniciando verificação de conexão.');
    const statusDiv = document.getElementById('connection-status');
    const loginForm = document.getElementById('login-form');
    const loginButton = document.getElementById('login-button');
    const loginText = document.getElementById('login-text');
    const loginSpinner = document.getElementById('login-spinner');
    const loginSuccess = document.getElementById('login-success');
    
    // Testar conexão com o Supabase
    fetch('/auth/test-connection')
        .then(response => {
            console.log('Resposta da verificação de conexão recebida:', response);
            return response.json();
        })
        .then(data => {
            console.log('Dados da verificação de conexão:', data);
            if (data.status === 'success') {
                statusDiv.className = 'connection-status-box alert-success mb-3';
                statusDiv.innerHTML = `
                    <div class="flex items-center">
                        <div class="w-3 h-3 rounded-full bg-green-500 mr-2 animate-pulse"></div>
                        <span>Conexão com o Banco de dados</span>
                    </div>
                `;
            } else {
                statusDiv.className = 'connection-status-box alert-danger mb-3';
                statusDiv.innerHTML = `
                    <div class="flex items-center">
                        <div class="w-3 h-3 rounded-full bg-red-500 mr-2 animate-pulse"></div>
                        <span>Conexão com o Banco de dados</span>
                    </div>
                `;
            }
        })
        .catch(error => {
            console.error('Erro ao verificar conexão:', error);
            statusDiv.className = 'connection-status-box alert-danger mb-3';
            statusDiv.innerHTML = `
                <div class="flex items-center">
                    <div class="w-3 h-3 rounded-full bg-red-500 mr-2 animate-pulse"></div>
                    <span>Conexão com o Banco de dados</span>
                </div>
            `;
        });
        
    // Animação do botão de login
    loginForm.addEventListener('submit', function(e) {
        e.preventDefault();
        console.log('Formulário de login enviado.');

        // Validação frontend
        const email = loginForm.querySelector('input[name="email"]').value.trim();
        const password = loginForm.querySelector('input[name="password"]').value.trim();
        console.log('Dados coletados do formulário:', { email, password });

        // Remover alertas antigos
        const oldAlert = loginForm.querySelector('.alert-danger');
        if (oldAlert) oldAlert.remove();
        if (!email || !password) {
            console.warn('Email ou senha ausentes.');
            // Exibe erro sem recarregar
            const alert = document.createElement('div');
            alert.className = 'rounded-md p-4 mb-4 alert-danger';
            alert.innerText = 'Email e senha são obrigatórios.';
            loginForm.insertBefore(alert, loginForm.firstChild);
            return;
        }

        console.log('Enviando dados do formulário para o backend.');
        // Mostrar spinner
        loginText.classList.add('hidden');
        loginSpinner.classList.remove('hidden');
        loginButton.classList.add('loading');
        loginButton.disabled = true;
        // Collect form data
        const formData = new FormData(loginForm);
        // Send form data via fetch
        fetch('/auth/login', {
            method: 'POST',
            body: formData,
            headers: {
                'X-Requested-With': 'XMLHttpRequest'
            }
        })
        .then(response => {
            console.log('Resposta do login recebida:', response);
            if (response.redirected) {
                console.log('Redirecionamento detectado para:', response.url);
                // Se for redirecionado, mostrar animação de sucesso primeiro
                loginSpinner.classList.add('hidden');
                loginSuccess.classList.remove('hidden');
                loginSuccess.classList.add('success-animate');
                loginButton.classList.remove('loading');
                loginButton.classList.add('success');
                setTimeout(() => {
                    window.location.href = response.url;
                }, 600);
                return;
            }
            return response.text();
        })
        .then(html => {
            if (html) {
                console.log('HTML recebido do backend:', html);
                loginSpinner.classList.add('hidden');
                loginText.classList.remove('hidden');
                loginButton.classList.remove('loading');
                loginButton.disabled = false;
                // Procurar por mensagens de erro no HTML
                const parser = new DOMParser();
                const doc = parser.parseFromString(html, 'text/html');
                const errorMessages = doc.querySelectorAll('.alert-danger');
                if (errorMessages.length > 0) {
                    // Se houver uma mensagem de erro no retorno, atualize a página com ela
                    document.documentElement.innerHTML = html;
                }
            }
        })
        .catch(error => {
            console.error('Erro durante o login:', error);
            loginSpinner.classList.add('hidden');
            loginText.classList.remove('hidden');
            loginButton.classList.remove('loading');
            loginButton.disabled = false;
        });
    });
});