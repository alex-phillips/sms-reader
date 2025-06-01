import { Center, Modal } from "@mantine/core";
import type { Media } from "../types";

export default function MediaModal({
  media,
  opened,
  onClose,
}: {
  media: Media | null;
  opened: boolean;
  onClose: () => void;
}) {
  if (!media) {
    return <></>;
  }

  return (
    <Modal size="auto" fullScreen opened={opened} onClose={onClose}>
      {media && (
        <Center>
          {media.content_type.match("video") && (
            <video
              controls={true}
              style={{ maxHeight: "calc(98vh - 60px)", maxWidth: "100%" }}
            >
              <source src={`/api/media/${media.id}/cache`} />
            </video>
          )}
          {media.content_type.match("image") && (
            <img
              src={`/api/media/${media.id}/cache`}
              alt={media.filename}
              style={{ maxHeight: "calc(98vh - 60px)", maxWidth: "100%" }}
            />
          )}
        </Center>
      )}
    </Modal>
  );
}
