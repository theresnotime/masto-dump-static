import json
import os
import re
import settings
import shutil
from datetime import datetime

get_actor = re.compile(r"https?:\/\/(?P<instance>.*?)\/.*?\/(?P<user>.*?)$")
check_reply = re.compile(r"<p>@|<p>(<span|<a).*?@", re.IGNORECASE)


def checkPost(post: object) -> str | None:
    """Check if a post is valid for inclusion in the archive

    Args:
        post (object): Post object

    Returns:
        str | None: HTML content of the post or None
    """
    if (
        post["object"]["inReplyTo"] is None
        and len(post["object"]["cc"]) == 1
        and post["object"]["sensitive"] is False
        and check_reply.search(post["object"]["content"]) is None
    ):
        content = post["object"]["content"]
        return renderMarkdown(content)
    else:
        return None


def renderMarkdown(content: str) -> str:
    """Convert some select markdown to HTML

    Args:
        content (str): Post content in HTML

    Returns:
        str: Rendered content
    """
    content = re.sub(r"`(?P<md>.*?)`", "<code>\g<md></code>", content)
    content = re.sub(r"\*(?P<md>\w+)\*", "<em>\g<md></em>", content)
    return content


def wrapPost(post: str, timestamp: str, actor: str, status_url: str) -> str:
    """Wraps a post in the necessary HTML

    Args:
        post (str): Post content in HTML
        timestamp (str): Wrapped timestamp
        actor (str): Wrapped actor
        status_url (str): Wrapped status URL

    Returns:
        str: Wrapped post content
    """
    return f'<article class="status__wrapper status__wrapper-unlisted focusable">{actor}{timestamp}<div class="status__content prose">{post}</div>{status_url}</article>'


def wrapPostLink(status_url: str) -> str:
    """Wraps the post link in the necessary HTML

    Args:
        status_url (str): Unwrapped status URL

    Returns:
        str: Wrapped status URL
    """
    return f'<div class="status__status_url"><a href="{status_url}" rel="nofollow">View original post</a></div>'


def wrapTimestamp(timestamp: str) -> str:
    """Wraps the timestamp in the necessary HTML

    Args:
        timestamp (str): Unwrapped timestamp

    Returns:
        str: Wrapped timestamp
    """
    return f'<div class="status__timestamp" data-ts="{timestamp}"><a href="#{timestamp}">{timestamp}</a></div>'


def wrapActor(actor: str, timestamp: str) -> str:
    """Wrap the actor in the necessary HTML, and adds an anchor link

    Args:
        actor (str): Unwrapped actor
        timestamp (str): Unwrapped timestamp

    Returns:
        str: Wrapped actor
    """
    return f'<div class="status__actor"><h1 id="{timestamp}">{actor}</h1></div>'


def parseActor(actor: str) -> str | bool:
    """Parses the actor URL to get the username and instance

    Args:
        actor (str): Actor URL

    Returns:
        str | bool: @actor@instance or False
    """
    m = get_actor.match(actor)
    if m:
        return f"@{m.group('user')}@{m.group('instance')}"
    return False


def templateHeader() -> None:
    """Substitutes in the head template and writes to output file"""
    head = open("template/head.html", "r", encoding="utf-8").read()
    head = head.replace("{{title}}", settings.TITLE)
    head = head.replace("{{extra_meta}}", settings.EXTRA_META)
    with open(settings.OUT_FILE, "w") as out_file:
        out_file.write(head)


def templateFooter() -> None:
    """Substitutes in the footer template and writes to output file"""
    footer = open("template/footer.html", "r", encoding="utf-8").read()
    footer = footer.replace(
        "{{last_gen}}", datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    )
    footer = footer.replace("{{footer_text}}", settings.FOOTER_TEXT)
    with open(settings.OUT_FILE, "a") as out_file:
        out_file.write(footer)


if __name__ == "__main__":
    if not os.path.exists(settings.OUT_DIR):
        os.makedirs(settings.OUT_DIR)

    with open(settings.OUTBOX_FILE, "r", encoding="utf-8") as outbox_json:
        data = json.load(outbox_json)
        templateHeader()

        for i in data["orderedItems"]:
            if "content" in i["object"]:
                post = checkPost(i)
                if post is not None:
                    timestamp = wrapTimestamp(i["published"])
                    actor = wrapActor(parseActor(i["actor"]), i["published"])
                    status_url = wrapPostLink(i["object"]["id"])
                    with open(settings.OUT_FILE, "a") as out_file:
                        out_file.write(
                            wrapPost(post, timestamp, actor, status_url) + "\n"
                        )

        templateFooter()
        shutil.copy("fedi-archive-style.css", "out/")
