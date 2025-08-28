document.addEventListener('DOMContentLoaded', function() {
    console.log('Página carregada, iniciando verificação de conexão.');
    const statusDiv = document.getElementById('connection-status');
    const loginForm = document.getElementById('login-form');
    const loginButton = document.getElementById('login-button');
    const loginText = document.getElementById('login-text');
    const loginSpinner = document.getElementById('login-spinner');
    const loginSuccess = document.getElementById('login-success');
    
    // Add floating animation to bubbles on page load
    const bubbles = document.querySelectorAll('.shape');
    bubbles.forEach((bubble, index) => {
        // Add slight delay to each bubble for a staggered effect
        bubble.style.animationDelay = `${index * 0.5}s`;
    });
    
    // Add interactive effects to form elements
    const inputs = loginForm.querySelectorAll('input');
    inputs.forEach(input => {
        // Add focus effects
        input.addEventListener('focus', function() {
            this.parentElement.classList.add('ring-2', 'ring-unique-primary-medium', 'ring-opacity-50');
        });
        
        // Remove focus effects
        input.addEventListener('blur', function() {
            this.parentElement.classList.remove('ring-2', 'ring-unique-primary-medium', 'ring-opacity-50');
        });
    });
    
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
                        <span class="text-unique-success font-medium">Conexão com o Banco de dados estabelecida</span>
                    </div>
                `;
            } else {
                statusDiv.className = 'connection-status-box alert-danger mb-3';
                statusDiv.innerHTML = `
                    <div class="flex items-center">
                        <div class="w-3 h-3 rounded-full bg-red-500 mr-2 animate-pulse"></div>
                        <span class="text-unique-danger font-medium">Problemas na conexão com o Banco de dados</span>
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
                    <span class="text-unique-danger font-medium">Erro na verificação de conexão</span>
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
        
        // Add pulse animation to button
        loginButton.classList.add('animate-pulse');
        setTimeout(() => {
            loginButton.classList.remove('animate-pulse');
        }, 1000);
        
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
                
                // Add celebration effect
                createCelebrationEffect();
                
                setTimeout(() => {
                    window.location.href = response.url;
                }, 800);
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
            
            // Show error state
            loginButton.classList.add('bg-unique-danger');
            setTimeout(() => {
                loginButton.classList.remove('bg-unique-danger');
            }, 1000);
        });
    });
    
    // Function to create celebration effect on successful login
    function createCelebrationEffect() {
        const buttonRect = loginButton.getBoundingClientRect();
        const centerX = buttonRect.left + buttonRect.width / 2;
        const centerY = buttonRect.top + buttonRect.height / 2;
        
        // Create multiple floating elements
        for (let i = 0; i < 15; i++) {
            const particle = document.createElement('div');
            particle.style.position = 'fixed';
            particle.style.left = `${centerX}px`;
            particle.style.top = `${centerY}px`;
            particle.style.width = `${Math.random() * 10 + 5}px`;
            particle.style.height = particle.style.width;
            particle.style.backgroundColor = getRandomColor();
            particle.style.borderRadius = '50%';
            particle.style.zIndex = '1000';
            particle.style.pointerEvents = 'none';
            
            document.body.appendChild(particle);
            
            // Animate particle
            const angle = Math.random() * Math.PI * 2;
            const distance = 50 + Math.random() * 100;
            const duration = 1000 + Math.random() * 1000;
            
            particle.animate([
                { 
                    transform: 'translate(0, 0) scale(1)',
                    opacity: 1
                },
                { 
                    transform: `translate(${Math.cos(angle) * distance}px, ${Math.sin(angle) * distance}px) scale(0)`,
                    opacity: 0
                }
            ], {
                duration: duration,
                easing: 'cubic-bezier(0.215, 0.61, 0.355, 1)'
            });
            
            // Remove particle after animation
            setTimeout(() => {
                particle.remove();
            }, duration);
        }
    }
    
    // Function to get random company colors
    function getRandomColor() {
        const colors = [
            '#165672', // unique-primary-dark
            '#2d6b92', // unique-primary-medium
            '#4a8bb8', // unique-primary-light
            '#e2ba0a', // unique-accent
            '#f4d03f'  // unique-accent-light
        ];
        return colors[Math.floor(Math.random() * colors.length)];
    }
});