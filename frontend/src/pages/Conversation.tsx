import { useEffect, useRef, useState } from "react";
import {
  Box,
  ScrollArea,
  Stack,
  Text,
  Paper,
  Loader,
  Center,
  TextInput,
  ActionIcon,
  CloseIcon,
  CloseButton,
} from "@mantine/core";
import { useNavigate, useParams, useSearchParams } from "react-router-dom";
import type { Message, Conversation } from "../types";

const PAGE_SIZE = 50;

type ConversationMessagesResponse = {
  messages: Message[];
  has_more: boolean;
  has_newer: boolean;
  total: number;
};

// const SCROLL_THRESHOLD: number = 100;

function useDebounce(value, delay = 500) {
  const [debouncedValue, setDebouncedValue] = useState(value);

  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedValue(value);
    }, delay);

    return () => clearTimeout(handler); // Cleanup timeout on unmount or value change
  }, [value, delay]);

  return debouncedValue;
}

export default function Conversation() {
  const { conversationId } = useParams();
  const navigate = useNavigate();

  const [searchParams] = useSearchParams();
  const startMessageId = searchParams.get("startMessageId");

  const [messages, setMessages] = useState<Message[]>([]);
  const [hasMore, setHasMore] = useState(true);
  const [hasNewer, setHasNewer] = useState(true);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState<string>("");

  const debouncedSearch = useDebounce(search);

  const skipScrollEvent = useRef(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const innerRef = useRef<HTMLDivElement>(null);
  const firstLoad = useRef(true);

  const fetchMessages = async (
    conversationId: string | undefined,
    {
      beforeId,
      afterId,
      limit = 50,
    }: { beforeId?: number; afterId?: number; limit?: number } = {}
  ): Promise<ConversationMessagesResponse> => {
    const params = new URLSearchParams({ limit: limit.toString() });

    if (beforeId) {
      params.append("start_before_message_id", beforeId.toString());
    } else if (afterId) {
      params.append("start_after_message_id", afterId.toString());
    }

    const res = await fetch(
      `/api/conversation/${conversationId}/messages?${params.toString()}`
    );
    if (!res.ok) {
      throw new Error("Failed to fetch messages");
    }
    return await res.json();
  };

  const fetchInitialMessages = async (startingId: string | null = null) => {
    const startAt = startingId || startMessageId;

    setLoading(true);
    try {
      let data;
      if (startAt) {
        data = await fetchMessages(conversationId, {
          beforeId: parseInt(startAt) + 5, // Add a couple so we have padding
          limit: PAGE_SIZE,
        });
      } else {
        data = await fetchMessages(conversationId, { limit: PAGE_SIZE });
      }

      setMessages(data.messages.reverse()); // reverse so oldest at top
      setHasMore(data.has_more);
      setHasNewer(data.has_newer);

      // Programmatic scroll to startAt or bottom
      skipScrollEvent.current = true; // disable scroll handling temporarily
      setTimeout(() => {
        if (startAt) {
          const el = document.getElementById(`message-${startAt}`);
          if (el && scrollRef.current) {
            scrollRef.current.scrollTo({ top: el.offsetTop });
          } else {
            scrollRef.current?.scrollTo({
              top: scrollRef.current.scrollHeight,
            });
          }
        } else {
          scrollRef.current?.scrollTo({ top: scrollRef.current.scrollHeight });
        }

        // Re-enable scroll handling after short delay
        setTimeout(() => {
          skipScrollEvent.current = false;
        }, 500); // 200ms should be enough, adjust if needed
      }, 0);
    } finally {
      setLoading(false);
    }
  };

  const loadOlderMessages = async () => {
    if (!hasMore || loading) return;
    setLoading(true);
    const oldest = messages[0];
    try {
      const data = await fetchMessages(conversationId, {
        beforeId: oldest.id,
      });
      setMessages((prev) => [...data.messages.reverse(), ...prev]);
      setHasMore(data.has_more);
    } finally {
      setLoading(false);
    }

    if (innerRef.current && !firstLoad.current) {
      const prevHeight = innerRef.current.scrollHeight;
      requestAnimationFrame(() => {
        if (innerRef.current) {
          const newHeight = innerRef.current.scrollHeight;
          scrollRef.current!.scrollTop += newHeight - prevHeight;
        }
      });
    }
  };

  const loadNewerMessages = async () => {
    if (!hasNewer || loading) return;
    setLoading(true);
    const newest = messages[messages.length - 1];
    try {
      const data = await fetchMessages(conversationId, {
        afterId: newest.id,
      });
      setMessages((prev) => [...prev, ...data.messages.reverse()]);

      const el = document.getElementById(`message-${newest.id}`);
      if (el && scrollRef.current) {
        scrollRef.current.scrollTo({ top: el.offsetTop });
      } else {
        scrollRef.current?.scrollTo({
          top: scrollRef.current.scrollHeight,
        });
      }

      setHasNewer(data.has_newer);
    } finally {
      setLoading(false);
    }
  };

  const searchMessages = async () => {
    if (!search) return;

    skipScrollEvent.current = false;
    const params = new URLSearchParams({ query: search });
    const res = await fetch(
      `/api/conversation/${conversationId}/search?${params.toString()}`
    );
    if (!res.ok) {
      throw new Error("Failed to fetch messages");
    }
    setMessages(await res.json());
    setHasMore(false);
    setHasNewer(false);
  };

  useEffect(() => {
    fetchInitialMessages();
  }, [conversationId]);

  useEffect(() => {
    // Scroll to bottom on initial load
    if (scrollRef.current && firstLoad.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
      firstLoad.current = false;
    }
  }, [messages]);

  useEffect(() => {
    searchMessages();
  }, [debouncedSearch]);

  const handleScroll = () => {
    if (skipScrollEvent.current) return; // ignore scroll events during skip window
    if (!scrollRef.current) return;
    const el = scrollRef.current;

    if (el.scrollTop < 50) {
      loadOlderMessages();
    } else if (el.scrollHeight - el.scrollTop - el.clientHeight < 50) {
      loadNewerMessages();
    }
  };

  const onSearchChange = (event: React.ChangeEvent<HTMLInputElement>) => {
    const { value } = event.target;
    setSearch(value);
  };

  const reset = () => {
    setSearch("");
    navigate(`/conversation/${conversationId}`);
    fetchInitialMessages();
  };

  const goToMessage = (messageId: number) => {
    if (search) {
      // navigate(`/conversation/${conversationId}?startMessageId=${messageId}`)
      fetchInitialMessages(messageId.toString());
    }
  };

  return (
    <>
      <ScrollArea
        style={{ height: "calc(100vh - 140px)" }}
        viewportRef={scrollRef}
        onScrollPositionChange={handleScroll}
      >
        <Stack ref={innerRef} p="md">
          {loading && (
            <Center>
              <Loader />
            </Center>
          )}

          {messages.map((msg) => {
            const isSent = msg.direction === "sent";

            return (
              <Stack
                gap="2"
                id={`message-${msg.id}`}
                onClick={() => goToMessage(msg.id)}
              >
                {!isSent && (
                  <Text size="xs" c="red" fw={700} pl={10}>
                    {msg.contact}
                  </Text>
                )}
                <Box
                  key={msg.id}
                  style={{
                    display: "flex",
                    justifyContent: isSent ? "flex-end" : "flex-start",
                  }}
                >
                  <Paper
                    shadow="sm"
                    radius="lg"
                    p="sm"
                    maw="50%"
                    style={{
                      color: "white",
                      backgroundColor: isSent ? "#0b57d0" : "#303030",
                      border: isSent
                        ? "1px solid #0b57d0"
                        : "1px solid #303030",
                    }}
                  >
                    {msg.text && <Text size="sm">{msg.text}</Text>}
                    {msg.media.map((media) => {
                      console.log(media);
                      return (
                        <div key={media.id}>
                          {media.content_type.match("video") && (
                            <video
                            controls={true}
                            style={{ maxHeight: "50vh", maxWidth: "100%" }}
                          >
                            <source src={`/api/media/${media.id}/cache`} />
                          </video>
                          )}
                          {media.content_type.match("image") && (
                            <img
                              src={`/api/media/${media.id}/cache`}
                              alt={media.filename}
                              style={{ maxHeight: "50vh", maxWidth: "100%" }}
                            />
                          )}
                        </div>
                      );
                    })}
                    <Text
                      size="xs"
                      c="gray"
                      ta={isSent ? "right" : "left"}
                      mt={4}
                    >
                      {new Date(msg.date).toLocaleString()}
                    </Text>
                  </Paper>
                </Box>
              </Stack>
            );
          })}
        </Stack>
      </ScrollArea>

      <TextInput
        placeholder="Search"
        value={search}
        onChange={onSearchChange}
        rightSection={<CloseButton onClick={reset} />}
      />
    </>
  );
}
