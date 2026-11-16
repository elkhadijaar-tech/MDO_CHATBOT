from . import create_app
from .config import get_config

if __name__ == "__main__":
    cfg = get_config()
    app = create_app()
    mode = "IA (" + cfg["LLM_PROVIDER"] + ")" if cfg["LLM_API_KEY"] else "DÉMO (aucune clé API : réponses extraites de la base, sans IA)"
    print(f"\n MDO CHATBOT - MDO ESTC  |  mode : {mode}")
    print(f" Ouvrez : http://{cfg['HOST']}:{cfg['PORT']}\n (Ctrl+C pour arrêter)\n")
    app.run(host=cfg["HOST"], port=cfg["PORT"], debug=False, threaded=True)
