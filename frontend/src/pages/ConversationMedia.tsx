import { useEffect, useRef, useState } from "react";
import {
  ScrollArea,
  Stack,
  Loader,
  Center,
  Grid,
  Tooltip,
  ActionIcon,
} from "@mantine/core";
import { useNavigate, useParams } from "react-router-dom";
import type { ConversationMedia } from "../types";
import { ExternalLink } from "lucide-react";

const PAGE_SIZE = 30;

type ConversationMediaResponse = {
  media: ConversationMedia[];
  has_more: boolean;
  total: number;
};

export default function ConversationMedia() {
  const { conversationId } = useParams();

  const navigate = useNavigate();

  const [media, setMedia] = useState<ConversationMedia[]>([]);
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(true);
  const [loading, setLoading] = useState(false);

  const scrollRef = useRef<HTMLDivElement>(null);
  const innerRef = useRef<HTMLDivElement>(null);
  const firstLoad = useRef(true);

  const fetchMedia = async (newOffset: number) => {
    if (newOffset != 0) {
      if (!hasMore || loading) return;
    }
    setLoading(true);
    try {
      const url = new URL(
        `/api/conversation/${conversationId}/media`,
        window.location.origin
      );
      url.searchParams.set("offset", newOffset.toString());
      url.searchParams.set("limit", PAGE_SIZE.toString());

      const res: ConversationMediaResponse = await (
        await fetch(url.toString())
      ).json();

      const newMedia = res.media.sort((a, b) => (a.date < b.date ? 1 : -1));
      setHasMore(res.has_more);
      setOffset(newOffset + newMedia.length);

      // Prepend older messages
      console.log(newOffset);
      if (newOffset > 0) {
        setMedia((prev) => [...prev, ...newMedia]);
      } else {
        setMedia(newMedia);
      }

      // Maintain scroll position after prepend
      if (newOffset > 0) {
        if (innerRef.current && !firstLoad.current) {
          const prevHeight = innerRef.current.scrollHeight;
          requestAnimationFrame(() => {
            if (innerRef.current) {
              const newHeight = innerRef.current.scrollHeight;
              scrollRef.current!.scrollTop += newHeight - prevHeight;
            }
          });
        }
      }
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchMedia(0);
  }, []);

  useEffect(() => {
    // Scroll to bottom on initial load
    if (scrollRef.current && firstLoad.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
      firstLoad.current = false;
    }
  }, [media]);

  const handleScroll = () => {
    if (!scrollRef.current || loading || !hasMore) return;

    const { scrollTop, scrollHeight, clientHeight } = scrollRef.current;

    if (scrollTop + clientHeight >= scrollHeight - 100) {
      fetchMedia(offset);
    }
  };

  const goToMessage = (messageId: number) => {
    navigate(`/conversation/${conversationId}?startMessageId=${messageId}`);
  };

  return (
    <>
      <ScrollArea
        style={{ height: window.innerHeight - 100 }}
        viewportRef={scrollRef}
        onScrollPositionChange={handleScroll}
      >
        <Stack ref={innerRef} p="md">
          {loading && offset === 0 && (
            <Center>
              <Loader />
            </Center>
          )}

          <div
            style={{
              resize: "horizontal",
              overflow: "hidden",
              maxWidth: "100%",
            }}
          >
            <Grid
              type="container"
              breakpoints={{
                xs: "100px",
                sm: "200px",
                md: "300px",
                lg: "400px",
                xl: "500px",
              }}
            >
              {media.map((item) => {
                console.log(item);
                return (
                  <Grid.Col span={{ base: 12, md: 6, lg: 3 }}>
                    <Tooltip label={new Date(item.date).toLocaleString()}>
                      <div key={item.id} style={{ position: "relative" }}>
                        {item.content_type.match("video") && (
                          <video
                            controls={true}
                            style={{ maxHeight: "50vh", maxWidth: "100%" }}
                          >
                            <source src={`/api/media/${item.id}/cache`} />
                          </video>
                        )}
                        {item.content_type.match("image") && (
                          <img
                            src={`/api/media/${item.id}/cache`}
                            alt={item.filename}
                            style={{ width: "100%" }}
                          />
                        )}
                        <ActionIcon
                          onClick={() => goToMessage(item.message_id)}
                          variant="transparent"
                          color="white"
                          style={{
                            position: "absolute",
                            top: 0,
                            right: 0,
                            zIndex: 1,
                          }}
                        >
                          <ExternalLink />
                        </ActionIcon>
                      </div>
                    </Tooltip>
                  </Grid.Col>
                );
              })}
            </Grid>
          </div>

          {loading && offset > 0 && (
            <Center>
              <Loader size="sm" />
            </Center>
          )}
        </Stack>
      </ScrollArea>
    </>
  );
}
