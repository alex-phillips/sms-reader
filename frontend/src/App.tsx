import { useEffect, useState } from "react";
import { Outlet, useLocation, useNavigate, useParams } from "react-router-dom";
import {
  AppShell,
  Burger,
  Group,
  MantineProvider,
  ScrollArea,
  Text,
  TextInput,
  Tooltip,
  NavLink,
  Button,
  Paper,
  Divider,
  CloseButton,
  ActionIcon,
} from "@mantine/core";
import type { Conversation } from "./types";
import { Link } from "react-router-dom";
import { ArrowLeft, Image } from "lucide-react";

export default function App() {
  const loc = useLocation();
  const navigate = useNavigate();
  const { conversationId } = useParams();

  const [drawerOpen, setDrawerOpen] = useState<boolean>(false);
  const [asideOpen, setAsideOpen] = useState<boolean>(false);
  const [conversations, setConversations] = useState<Conversation[]>([]);
  const [filteredConversations, setFilteredConctacts] =
    useState<Conversation[]>(conversations);
  const [search, setSearch] = useState<string>("");
  const [header, setHeader] = useState<string>("Messages");
  const [activeConvoId, setActiveConvoId] = useState<string>(
    `${conversationId}`
  );
  const [activeConvo, setActiveConvo] = useState<Conversation | null>(null);

  useEffect(() => {
    async function fetchConversations() {
      fetch("/api/conversations")
        .then((res) => res.json())
        .then((data) => {
          setConversations(data);
          setFilteredConctacts(data);
        });
    }

    fetchConversations();
  }, []);

  useEffect(() => {
    setActiveConvo(
      conversations.find((c) => c.id == parseInt(activeConvoId)) || null
    );
    console.log(conversations.find((c) => c.id == parseInt(activeConvoId)));
  }, [conversations, activeConvoId]);

  const onSearch = (event: React.ChangeEvent<HTMLInputElement>) => {
    const searchString = event.target.value;
    setSearch(searchString);
    setFilteredConctacts(
      conversations.filter((conversation) => {
        const re = new RegExp(searchString, "ig");
        return conversation.name?.match(re);
      })
    );
  };

  const selectConversation = (conversation: Conversation) => {
    setDrawerOpen(false);
    setHeader(conversation.name || "");
    setActiveConvoId(conversation.id.toString());
  };

  const toggleDrawer = () => {
    setDrawerOpen(!drawerOpen);
  };

  const toggleAside = () => {
    setAsideOpen(!asideOpen);
  };

  return (
    <MantineProvider defaultColorScheme="dark">
      <AppShell
        layout="alt"
        header={{ height: 60 }}
        navbar={{
          width: 300,
          breakpoint: "sm",
          collapsed: { mobile: !drawerOpen, desktop: !drawerOpen },
        }}
        aside={{
          width: 300,
          breakpoint: "sm",
          collapsed: { desktop: !asideOpen, mobile: !asideOpen },
        }}
        padding="md"
      >
        <AppShell.Header>
          <Group h="100%" w="100%" px="md">
            <Burger opened={drawerOpen} onClick={toggleDrawer} />
            <Group justify="space-between">
              <Tooltip label={header} multiline position="bottom-start">
                <Text
                  size="lg"
                  fw={700}
                  style={{
                    width:
                      drawerOpen && asideOpen
                        ? "calc(100vw - 780px)"
                        : drawerOpen || asideOpen
                        ? "calc(100vw - 480px)"
                        : "calc(100vw - 180px)",
                    overflow: "hidden",
                    whiteSpace: "nowrap",
                    textOverflow: "ellipsis",
                  }}
                >
                  {header}
                </Text>
              </Tooltip>

              {loc.pathname.endsWith("/media") && (
                <ActionIcon
                  variant="transparent"
                  color="white"
                  onClick={() => navigate(`/conversation/${activeConvoId}`)}
                >
                  <ArrowLeft />
                </ActionIcon>
              )}
              {!loc.pathname.endsWith("/media") && (
                <ActionIcon
                  variant="transparent"
                  color="white"
                  onClick={() =>
                    navigate(`/conversation/${activeConvoId}/media`)
                  }
                >
                  <Image />
                </ActionIcon>
              )}

              <Burger opened={asideOpen} onClick={toggleAside} />
            </Group>
          </Group>
        </AppShell.Header>

        <AppShell.Navbar p="md">
          <TextInput placeholder="Search" value={search} onChange={onSearch} />

          <ScrollArea>
            {filteredConversations.map((conversation) => (
              <NavLink
                component={Link}
                to={`/conversation/${conversation.id}`}
                label={conversation.name}
                active={conversation.id == activeConvoId}
                onClick={() => selectConversation(conversation)}
              />
            ))}
          </ScrollArea>
        </AppShell.Navbar>

        <AppShell.Main>
          <Outlet />
        </AppShell.Main>

        <AppShell.Aside p="md">
          <Group justify="space-between">
            <Text fw={700} size="lg">
              Details
            </Text>

            <CloseButton onClick={() => setAsideOpen(false)} />
          </Group>

          <Divider />

          {activeConvo?.contacts?.map((contact) => (
            <Paper
              shadow="sm"
              radius="sm"
              p="xs"
              style={{
                backgroundColor: "#303030",
                marginTop: 5,
                marginBottom: 5,
              }}
            >
              <Group justify="space-between">
                <Text size="sm">{contact.contact_name}</Text>
                <Text size="sm">{contact.address}</Text>
              </Group>
            </Paper>
          ))}
        </AppShell.Aside>
      </AppShell>
    </MantineProvider>
  );
}
