# ReMD

GitHub や Azure DevOps にあるソースコードを、**1つのテキストファイル（Markdown）にまとめて保存**するツールです。
ブラウザで操作するだけなので、プログラミングの知識は不要です。

---

## どんなときに使う？

- AI（ChatGPT / Claude など）にソースコードを読ませたいとき
- リポジトリの中身をざっと確認したいとき
- コードレビュー用に全ファイルを1つにまとめたいとき

---

## 使い方（3ステップ）

### 1. アプリを起動する

配布された **ReMD** ファイルをダブルクリックします。
しばらく待つと、ブラウザが自動で開きます。

> もしブラウザが開かない場合は、手動で http://localhost:8501 にアクセスしてください。

### 2. リポジトリの URL を貼り付けて「Convert」

ブラウザに表示された画面で、以下の手順で操作します。

1. **Repository URL** 欄に、GitHub や Azure DevOps のリポジトリ URL を貼り付ける
2. 必要に応じてフィルタやオプションを設定する（後述）
3. **Convert** ボタンを押す

変換が始まると、プログレスバーで進捗が表示されます。

### 3. ダウンロード

変換が完了すると **Download Markdown** ボタンが表示されます。
クリックすると `.md` ファイルがダウンロードされます。

---

## オプション設定

画面左のサイドバーで設定できます。

| 項目 | 説明 |
|---|---|
| **GitHub Token** | 非公開リポジトリを読み込む場合に入力します（公開リポジトリなら不要） |
| **Azure DevOps PAT** | Azure DevOps の非公開リポジトリを読み込む場合に入力します |
| **Max file size (MB)** | 指定サイズを超えるファイルはスキップされます（初期値: 1 MB） |

### ファイルフィルタ（正規表現）

特定の種類のファイルだけを取り込みたい場合に使います。
**File filter** 欄にパターンを入力してください。カンマ区切りで複数指定できます。

**よく使う例：**

| やりたいこと | 入力する値 |
|---|---|
| Python ファイルだけ | `\.py$` |
| Python と TypeScript | `\.py$, \.ts$` |
| src フォルダの中だけ | `^src/` |
| テストファイルを除外したい | ― （現在は「含めるパターン」のみ対応） |

> 入力した正規表現が間違っている場合は、入力欄が赤くなりエラーが表示されます。
> 空欄のままなら全ファイルが対象になります。

---

## 対応している URL の形式

| サービス | URL の例 |
|---|---|
| GitHub | `https://github.com/owner/repo` |
| GitHub（ブランチ指定） | `https://github.com/owner/repo/tree/main` |
| Azure DevOps（新形式） | `https://dev.azure.com/org/project/_git/repo` |
| Azure DevOps（旧形式） | `https://org.visualstudio.com/project/_git/repo` |

---

## GitHub Token の取得方法

非公開リポジトリを使う場合のみ必要です。

1. GitHub にログイン
2. 右上のアイコン → **Settings** → 左メニュー最下部 **Developer settings**
3. **Personal access tokens** → **Tokens (classic)** → **Generate new token**
4. `repo` にチェックを入れて生成
5. 表示されたトークンをコピーして、アプリのサイドバーに貼り付け

> トークンは画面を閉じると表示されなくなります。安全な場所にメモしてください。

---

## Azure DevOps PAT の取得方法

1. Azure DevOps にログイン
2. 右上のユーザーアイコン → **Personal access tokens**
3. **New Token** → Scopes で **Code (Read)** にチェック → **Create**
4. 表示されたトークンをコピーして、アプリのサイドバーに貼り付け

---

## URL で項目を事前入力する（クエリパラメータ）

ブラウザの URL にパラメータを付けると、各項目をあらかじめ埋めた状態で開けます。
社内 Wiki やチャットにリンクを貼っておくと、チームメンバーがワンクリックで使えます。

```
http://localhost:8501/?url=https://github.com/owner/repo&filter=\.py$&max_size=2
```

| パラメータ | 対応する項目 | 例 |
|---|---|---|
| `url` | Repository URL | `url=https://github.com/owner/repo` |
| `filter` | File filter（正規表現） | `filter=\.py$` |
| `token` | GitHub Token | `token=ghp_xxxx` |
| `pat` | Azure DevOps PAT | `pat=xxxx` |
| `max_size` | Max file size (MB) | `max_size=2` |

> 複数のフィルタはカンマ区切りで指定します: `filter=\.py$,\.ts$`

---

## 終了方法

ブラウザのタブを閉じると、アプリは自動で終了します。

> もしプロセスが残ってしまう場合は、起動時に開いたコンソール（黒い画面）を閉じてください。

---

## うまくいかないとき

| 症状 | 対処法 |
|---|---|
| 「Repository not found」と表示される | URL が正しいか確認してください。非公開リポジトリの場合はトークンが必要です |
| 「Rate limit exceeded」と表示される | GitHub Token を設定すると、1時間あたりの上限が 60回 → 5,000回 に増えます |
| 変換が途中で止まる | ファイル数が多い場合は時間がかかります。Max file size を小さくすると速くなります |
| ブラウザが開かない | http://localhost:8501 に手動でアクセスしてください |

---

## 開発者向け情報

### ローカルで実行（Python 3.10 以上）

```bash
pip install streamlit requests
PYTHONPATH=src streamlit run src/ReMD/app.py
```

### テスト実行

```bash
pip install pytest responses
python -m pytest tests/ -v
```

### exe ビルド

OS に合わせてスクリプトを実行するだけで、依存パッケージのインストールからビルドまで自動で行われます。

| OS | 実行方法 |
|---|---|
| **macOS** | ターミナルで `./build.sh` を実行 |
| **Windows 10 / 11** | `build.bat` をダブルクリック |

> 前提条件: Python 3.10 以上がインストールされていること

ビルドが完了すると `dist/ReMD/` フォルダに成果物が出力されます。

| OS | 実行ファイル |
|---|---|
| macOS | `dist/ReMD/ReMD` |
| Windows | `dist\ReMD\ReMD.exe` |

#### 手動ビルド（上級者向け）

スクリプトを使わず直接ビルドしたい場合:

```bash
pip install streamlit requests pyinstaller
python build.py
```
