document.addEventListener('DOMContentLoaded', () => {
    const tabLinks = document.querySelectorAll('#main-tabs .nav-link');
    const tabContents = document.querySelectorAll('.tab-content');

    tabLinks.forEach(link => {
        link.addEventListener('click', event => {
            event.preventDefault();
            const targetId = link.getAttribute('data-tab');

            // Remove 'active' de todos os links e oculta conteúdos
            tabLinks.forEach(l => l.classList.remove('active'));
            tabContents.forEach(c => c.classList.add('d-none'));

            // Ativa o link clicado e mostra o conteúdo correspondente
            link.classList.add('active');
            document.getElementById(targetId).classList.remove('d-none');
        });
    });
});
