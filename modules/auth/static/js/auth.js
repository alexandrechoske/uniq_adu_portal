document.addEventListener('DOMContentLoaded', function() {
    console.log('Página carregada, iniciando verificação de conexão.');
    const statusDiv = document.getElementById('connection-status');
    const loginForm = document.getElementById('login-form');
    const loginButton = document.getElementById('login-button');
    const loginText = document.getElementById('login-text');
    const loginSpinner = document.getElementById('login-spinner');
    const loginSuccess = document.getElementById('login-success');
    const loginContainer = document.querySelector('.login-container');
    const loginCard = document.querySelector('.login-card');
    const loginContent = document.querySelector('.login-content');
    const logoImage = document.querySelector('.logo-section img');
    
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
        
        // Start the login animation
        startLoginAnimation();
        
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
                
                // Complete the animation and redirect
                setTimeout(() => {
                    showSuccessAnimation(response.url);
                }, 800);
                return;
            }
            return response.text();
        })
        .then(html => {
            if (html) {
                console.log('HTML recebido do backend:', html);
                // Reset animations if there's an error
                resetLoginAnimation();
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
            // Reset animations if there's an error
            resetLoginAnimation();
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
    
    // Function to start the login animation
    function startLoginAnimation() {
        // Create a circular animation container
        const circle = document.createElement('div');
        circle.id = 'login-circle';
        circle.innerHTML = `
            <div class="circle-inner">
                <img src="${logoImage.src}" alt="UniSystem" class="circle-logo">
                <div class="circle-spinner"></div>
            </div>
        `;
        document.body.appendChild(circle);
        
        // Hide the original content
        loginContainer.style.opacity = '0';
        loginContainer.style.visibility = 'hidden';
        
        // Trigger the animation
        setTimeout(() => {
            circle.classList.add('circle-animation');
        }, 50);
    }
    
    // Function to show success animation
    function showSuccessAnimation(redirectUrl) {
        const circle = document.getElementById('login-circle');
        if (circle) {
            // Change to checkmark
            circle.innerHTML = `
                <div class="circle-inner success">
                    <svg class="checkmark" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 52 52">
                        <circle class="checkmark-circle" cx="26" cy="26" r="25" fill="none"/>
                        <path class="checkmark-check" fill="none" d="M14.1 27.2l7.1 7.2 16.7-16.8"/>
                    </svg>
                </div>
            `;
            
            // Add success animation
            circle.classList.add('circle-success');
            
            // Redirect after animation completes
            setTimeout(() => {
                window.location.href = redirectUrl;
            }, 1000);
        }
    }
    
    // Function to reset animations if login fails
    function resetLoginAnimation() {
        // Remove the circle if it exists
        const circle = document.getElementById('login-circle');
        if (circle) {
            circle.remove();
        }
        
        // Show the original content
        loginContainer.style.opacity = '1';
        loginContainer.style.visibility = 'visible';
        loginText.classList.remove('hidden');
        loginSpinner.classList.add('hidden');
        loginButton.classList.remove('loading');
        loginButton.disabled = false;
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