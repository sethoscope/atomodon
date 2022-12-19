# Atomodon

This script gets the feed of a single Mastodon user and emits the
content as an Atom feed, suitable for feed readers. You could wrap
this and run it on a private server, or run it in a cron job to
generate a feed file locally.

The feed includes the same entries you'd find on a Mastodon
website (toots and boosts). Mastodon provides an RSS feed of toots
(primary/original content), but if you also want the boosts, you have to
work a bit harder.  The best solution would be for the Mastodon software
to provide such a feed, but in the meantime, here we are.

