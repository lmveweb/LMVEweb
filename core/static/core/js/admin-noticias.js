/* Formulario de Noticias en el panel: la casilla "Portada" de las fotos
   funciona como una sola opción. Al marcar una, se desmarcan las demás,
   así no hay que andar buscando cuál estaba marcada antes.

   En un archivo y no en el HTML: la política de seguridad del sitio
   (CSP) no deja correr scripts escritos dentro de la página. Si este
   archivo no carga, el servidor igual rechaza dos portadas marcadas
   (ver FotosFormSet en core/admin.py). */
(function () {
    'use strict';
    var PATRON = /^fotos-\d+-es_portada$/;

    document.addEventListener('change', function (evento) {
        var casilla = evento.target;
        if (!casilla.checked || !PATRON.test(casilla.name || '')) return;
        var todas = document.querySelectorAll('input[type="checkbox"][name$="-es_portada"]');
        for (var i = 0; i < todas.length; i++) {
            if (todas[i] !== casilla && PATRON.test(todas[i].name)) todas[i].checked = false;
        }
    });
})();
