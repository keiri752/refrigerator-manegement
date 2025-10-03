# 並行処理を行う（Flaskとpywebviewを同時に動かす必要があるため）
import threading
# Flaskなどのwebアプリをデスクトップアプリ風に表示できる
import webview
import app


def run_flask():
    app.app.run()


# Flaskを別スレッドで起動
flask_thread = threading.Thread(target=run_flask)
# メインスレッドが終わったら、サブスレッドも終了
# この場合、webviewが終わったらflaskも終了
flask_thread.daemon = True
# flaskを別で起動する命令
flask_thread.start()


# pywebviewで表示
webview.create_window("Flask Desktop App", "http://localhost:5000/")
webview.start()