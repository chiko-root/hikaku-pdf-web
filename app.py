import os
import logging
from flask import (
    Flask, render_template, request,
    send_file, flash, redirect, url_for
)
from werkzeug.utils import secure_filename
from compare_logic import compare_pdfs_with_color_coding
import pypdfium2

# 許可する拡張子
ALLOWED_EXT    = {'pdf'}
# アップロード／出力用フォルダ
UPLOAD_FOLDER  = 'uploads'
OUTPUT_FOLDER  = 'outputs'

app = Flask(
    __name__,
    static_folder='static',
    static_url_path='/static'
)
# flash() 用シークレットキー（本番では強力な値に変更）
app.secret_key = 'CHANGE_THIS_SECRET'
# ログレベル設定
app.logger.setLevel(logging.INFO)

# フォルダ作成
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)


def allowed_file(f):
    """許可拡張子チェック"""
    return (
        f
        and '.' in f.filename
        and f.filename.rsplit('.', 1)[1].lower() in ALLOWED_EXT
    )


def safe_delete(path: str):
    """ファイル削除時の例外を握りつぶし、ログに警告を出す"""
    try:
        if os.path.exists(path):
            os.remove(path)
    except Exception as e:
        app.logger.warning(f"ファイル削除に失敗: {path} → {e}")


def count_pdf_pages(path: str) -> int:
    """PDFのページ数を取得。失敗時はRuntimeErrorを投げる"""
    try:
        pdf = pypdfium2.PdfDocument(path)
        return len(pdf)
    except Exception as e:
        app.logger.error(f"ページ数取得失敗: {path} → {e}", exc_info=True)
        raise RuntimeError('PDFのページ数取得に失敗しました。')


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/compare', methods=['POST'])
def compare():
    # ファイル存在・拡張子チェック
    f_new = request.files.get('pdf1')
    f_old = request.files.get('pdf2')
    if not (allowed_file(f_new) and allowed_file(f_old)):
        flash('PDFファイルを2つアップロードしてください。')
        return redirect(url_for('index'))

    # 安全なファイル名で保存
    fn_new   = secure_filename(f_new.filename)
    fn_old   = secure_filename(f_old.filename)
    path_new = os.path.join(UPLOAD_FOLDER, fn_new)
    path_old = os.path.join(UPLOAD_FOLDER, fn_old)
    f_new.save(path_new)
    f_old.save(path_old)

    # ページ数チェック（取得失敗 or >10 はリダイレクト）
    try:
        pages_new = count_pdf_pages(path_new)
        pages_old = count_pdf_pages(path_old)
    except RuntimeError as e:
        safe_delete(path_new)
        safe_delete(path_old)
        flash(str(e))
        return redirect(url_for('index'))

    if pages_new > 10 or pages_old > 10:
        safe_delete(path_new)
        safe_delete(path_old)
        flash('PDFは10ページ以内のものをアップロードしてください。')
        return redirect(url_for('index'))

    # 色設定取得
    new_color = request.form.get('new_color', '赤')
    old_color = request.form.get('old_color', '青')

    # 差分比較実行
    try:
        out_pdf = compare_pdfs_with_color_coding(
            pdf1=path_new,
            pdf2=path_old,
            out_folder=OUTPUT_FOLDER,
            new_color=new_color,
            old_color=old_color
        )
        return send_file(
            os.path.abspath(out_pdf),
            as_attachment=True,
            download_name=os.path.basename(out_pdf),
            mimetype='application/pdf',
            max_age=0
        )
    except Exception as e:
        safe_delete(path_new)
        safe_delete(path_old)
        app.logger.error(f"比較エラー: {e}", exc_info=True)
        flash('比較中に予期せぬエラーが発生しました。')
        return redirect(url_for('index'))


@app.errorhandler(500)
def internal_error(e):
    """500エラー時に必ずキャッチし、ログ出力＆トップへリダイレクト"""
    app.logger.error(f"Unhandled Exception: {e}", exc_info=True)
    flash("予期せぬエラーが発生しました。しばらくしてから再度お試しください。")
    return redirect(url_for('index'))


if __name__ == '__main__':
    # 開発でも常に本番同様の挙動にする
    app.run(debug=False)