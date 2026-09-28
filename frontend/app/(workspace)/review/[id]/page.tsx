import ReceiptDetail from "@/components/receipt-detail";
export default async function ReviewPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  return <ReceiptDetail id={id} />;
}
