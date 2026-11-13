"""Read-only discovery of documents connected by Udanax Green links.

Green's FeBe protocol has no operation for enumerating every document in a
store.  We can discover a *connected component* from a known document via
find_links/follow_link, without parsing the on-disk enfilade format.
"""

import x88


def _documents_in_specs(specs):
    for spec in specs:
        if isinstance(spec, x88.VSpec):
            yield spec.docid
        elif isinstance(spec, x88.Span):
            # Non-virtual spans use global addresses with a document prefix.
            yield spec.start.split()[0]


def inspect_document(session, docid, already_open=False):
    """Return (short text excerpt, linked document IDs) for a read-only doc.

    Avoid closing the document currently displayed by Pyxi; opening and
    closing the same document from the discovery window can invalidate the
    editor's open-document state.
    """
    opened = None
    if not already_open:
        opened = session.open_document(docid, x88.READ_ONLY, x88.CONFLICT_COPY)
        docid = opened
    try:
        spans = session.retrieve_vspanset(docid)
        text_spans = [s for s in spans.spans if s.start[0] == 1]
        if not text_spans:
            return "(no text)", []
        textspec = x88.SpecSet(x88.VSpec(docid, text_spans))
        content = session.retrieve_contents(textspec)
        excerpt = " ".join("".join(part if isinstance(part, str) else str(part)
                           for part in content).split())[:90] or "(empty document)"

        # A document can be at either end of a link (backlinks matter).
        # The backend may return duplicate link IDs for overlapping ends.
        all_links = (session.find_links(textspec) +
                     session.find_links(x88.NOSPECS, textspec))
        unique_links = {str(link): link for link in all_links}
        neighbors = {}
        for link in unique_links.values():
            for end in (x88.LINK_SOURCE, x88.LINK_TARGET):
                for linked_id in _documents_in_specs(session.follow_link(link, end)):
                    if linked_id != docid:
                        neighbors[str(linked_id)] = linked_id
        return excerpt, [neighbors[key] for key in sorted(neighbors)]
    finally:
        if opened is not None:
            session.close_document(opened)
