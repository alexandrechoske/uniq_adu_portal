document.addEventListener('DOMContentLoaded', function() {
    // Exemplo de JS básico para o menu
    document.querySelectorAll('.menu-card').forEach(function(card) {
        card.addEventListener('mouseenter', function() {
            card.classList.add('hovered');
        });
        card.addEventListener('mouseleave', function() {
            card.classList.remove('hovered');
        });
    });
});
