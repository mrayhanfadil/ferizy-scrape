const APP_DEBUG = true;

if(!APP_DEBUG){
    if(!window.console) window.console = {};
    var methods = ["log", "debug", "warn", "info"];
    for(var i=0;i<methods.length;i++){
        console[methods[i]] = function(){};
    }
}

const doAddEventListener = () => {
    document.body.addEventListener(
        'click',
        function (evt) {
            if (
                evt?.target?.className &&
                typeof evt.target.className === 'string' &&
                evt.target.className.indexOf('modal fade') >= 0
            ) {
                let aa = document.getElementsByClassName('modal-backdrop');
                if (aa.length > 0) {
                    for (var i = 0; i < aa.length; i++) {
                        aa[i].style.display = 'none';
                    }
                }
            }
        },
        false
    );

    document.body.addEventListener(
        'change',
        function (evt) {
            if (
                evt?.target?.className &&
                typeof evt.target.className === 'string' &&
                evt.target.className.indexOf('border-red') >= 0
            ) {
                evt.target.classList.remove('border-red');
            }
        },
        false
    );
}

const addEventListenerWhenAvailable = () => {
	if (document && document.body && typeof document.body.addEventListener === 'function') {
		doAddEventListener();
	} else {
		setTimeout(addEventListenerWhenAvailable, 1000); // Check again after 100 milliseconds
	}
};

addEventListenerWhenAvailable();
